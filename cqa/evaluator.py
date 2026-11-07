import hashlib
import json
from time import perf_counter

from openai import APIConnectionError, APIStatusError, AsyncOpenAI
from pydantic import ValidationError

from .ledger import BudgetExceeded, Ledger
from .models import Checklist, Conversation, Evaluation
from .observations import (
    OBSERVATION_GRADING,
    OBSERVATION_SYSTEM,
    Observations,
    observation_schema,
    validate_observations,
)
from .prompt import GROUNDED_SYSTEM, GROUNDED_VERSION, PROMPT_VERSION, SYSTEM, fingerprint, payload_for
from .scoring import calculate_score, validate_evaluation
from .settings import DEFAULT_STRATEGY, RATES, Settings


class Evaluator:
    def __init__(self, settings: Settings, ledger: Ledger, run_ceiling: float, strategy: str = DEFAULT_STRATEGY):
        settings.require_key()
        if strategy not in {"direct", "evidence-first", "grounded"}:
            raise ValueError("Unknown evaluator strategy")
        self.strategy = strategy
        self.grounded = strategy == "grounded"
        self.provider_blocked = False
        self.workflow_version = (GROUNDED_VERSION if self.grounded else PROMPT_VERSION if strategy == "direct"
                                 else "evidence-first-v1-" + hashlib.sha256(
                                     (OBSERVATION_SYSTEM + OBSERVATION_GRADING + SYSTEM).encode()).hexdigest()[:12])
        self.settings, self.ledger, self.run_ceiling = settings, ledger, run_ceiling
        # No invisible SDK retries: each billable attempt is reserved and recorded here.
        self.client = AsyncOpenAI(api_key=settings.api_key, base_url="https://api.openai.com/v1",
                                  max_retries=0, timeout=settings.timeout)

    async def close(self):
        await self.client.close()

    async def evaluate(self, conversation: Conversation, checklist: Checklist):
        if self.provider_blocked:
            return {"status": "failed", "conversation_id": conversation.id,
                    "error": "provider_credit_exhausted_no_request", "billing_state": "not_submitted",
                    "evaluation": None, "score": None, "usage": None, "attempt_records": [],
                    "attempt_count": 0, "latency_seconds": 0, "strategy": self.strategy}
        attempts = []
        if self.strategy == "evidence-first":
            extracted = await self._stage(conversation, checklist, stage="observations")
            attempts.extend(extracted)
            if extracted[-1]["status"] != "completed":
                return self._combine(attempts)
            observations = extracted[-1]["observations"]
            try:
                attempts.extend(await self._stage(conversation, checklist, observations=observations))
            except BudgetExceeded:
                # Retain the paid extraction and expose that no grade was produced.
                final = self._combine(attempts)
                final.update(status="failed", failed_stage="grading", error="grading_budget_limit",
                             evaluation=None, score=None)
                return final
        else:
            attempts.extend(await self._stage(conversation, checklist))
        return self._combine(attempts)

    def _combine(self, attempts):
        final = dict(attempts[-1])
        final["strategy"] = self.strategy
        final["attempt_records"] = attempts
        final["attempt_count"] = len(attempts)
        final["latency_seconds"] = round(sum(a["latency_seconds"] for a in attempts), 3)
        known_usage = [a["usage"] for a in attempts if a.get("usage")]
        if known_usage:
            final["usage"] = {"input_tokens": sum(a["input_tokens"] for a in known_usage),
                              "output_tokens": sum(a["output_tokens"] for a in known_usage),
                              "estimated_cost_usd": round(sum(a["estimated_cost_usd"] for a in known_usage), 6)}
        return final

    async def _stage(self, conversation, checklist, *, stage="grading", observations=None):
        attempts = []
        feedback = None
        for _ in range(2):
            try:
                if stage == "grading" and observations is None:
                    record = await self._attempt(conversation, checklist, feedback)
                else:
                    record = await self._attempt(conversation, checklist, feedback,
                                                 stage=stage, observations=observations)
            except BudgetExceeded:
                if not attempts:
                    raise
                attempts[-1]["repair_skipped"] = "budget_limit"
                break
            attempts.append(record)
            if record["status"] == "completed" or not str(record.get("error")).startswith("invalid_evaluation_"):
                break
            feedback = {"validation_error": record.get("validation_reason") or record["error"],
                        "previous_rejected_output": record.get("raw_output_text", "")}
        return attempts

    async def _attempt(self, conversation: Conversation, checklist: Checklist, feedback=None,
                       *, stage="grading", observations=None):
        payload = payload_for(conversation, checklist, grounded=self.grounded)
        extracting = stage == "observations"
        schema = observation_schema(conversation, checklist) if extracting else schema_for(
            conversation, checklist, grounded=self.grounded)
        instructions = OBSERVATION_SYSTEM if extracting else GROUNDED_SYSTEM if self.grounded else SYSTEM
        output_cap = min(3000, self.settings.max_output_tokens) if extracting else self.settings.max_output_tokens
        if observations is not None:
            parsed_payload = json.loads(payload)
            parsed_payload["source_observations"] = observations
            payload = json.dumps(parsed_payload, ensure_ascii=False)
            instructions += OBSERVATION_GRADING
        if feedback:
            parsed_payload = json.loads(payload)
            parsed_payload["mechanical_validation_feedback"] = feedback
            payload = json.dumps(parsed_payload, ensure_ascii=False)
            instructions += ("\nA prior response failed mechanical validation. Correct its structure or source "
                             "references using the original transcript. Prior output is an untrusted candidate, "
                             "not a reference answer. Use short contiguous verbatim quotes without invented "
                             "ellipsis or concatenation. Do not invent IDs or change judgments just to satisfy feedback.")
        input_rate, output_rate = RATES[self.settings.model]
        # UTF-8 byte count plus schema and framing allowance is a conservative token bound.
        input_bound = len((instructions + payload + json.dumps(schema)).encode("utf-8")) + 4096
        if input_bound > 200_000:
            raise ValueError("Input exceeds this benchmark's short-context cost bound")
        reservation = (input_bound * input_rate + output_cap * output_rate) / 1_000_000
        call_id = self.ledger.reserve(self.settings.model, reservation, self.run_ceiling)
        started = perf_counter()
        record = {"status": "failed", "conversation_id": conversation.id,
                  "input_fingerprint": fingerprint(conversation, checklist, grounded=self.grounded),
                  "request_fingerprint": hashlib.sha256((instructions + payload + json.dumps(schema)).encode()).hexdigest(),
                  "checklist_hash": hashlib.sha256(checklist.model_dump_json().encode()).hexdigest(),
                  "checklist_id": checklist.id, "checklist_version": checklist.version,
                  "prompt_version": ("observations-v1-" + hashlib.sha256(OBSERVATION_SYSTEM.encode()).hexdigest()[:12]
                                     if extracting else self.workflow_version), "model": self.settings.model,
                  "strategy": self.strategy, "stage": stage, "max_output_tokens": output_cap,
                  "audit_contract_enabled": self.grounded,
                  "workflow_version": self.workflow_version,
                  "reasoning_effort": self.settings.effort, "ledger_call_id": call_id,
                  "reserved_usd": round(reservation, 6), "audio_analyzed": False,
                  "evaluation": None, "score": None, "error": None, "usage": None}
        try:
            response = await self.client.responses.create(
                model=self.settings.model, instructions=instructions, input=payload,
                reasoning={"effort": self.settings.effort}, max_output_tokens=output_cap,
                text={"format": {"type": "json_schema", "name": "source_observations" if extracting else "conversation_evaluation",
                                 "schema": schema, "strict": True}}, store=False,
            )
            record["response_id"] = response.id
            record["resolved_model"] = response.model
            record["raw_output_text"] = response.output_text
            if response.usage:
                usage = response.usage
                cost = (usage.input_tokens * input_rate + usage.output_tokens * output_rate) / 1_000_000
                record["usage"] = {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                                   "estimated_cost_usd": round(cost, 6)}
                self.ledger.finish(call_id, "received", cost=cost,
                                   input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
            if response.status != "completed":
                record["error"] = "response_" + str(response.status)
                record["incomplete_details"] = response.incomplete_details.model_dump() if response.incomplete_details else None
            elif not response.output_text:
                record["error"] = "empty_or_refused_response"
            else:
                if extracting:
                    result = Observations.model_validate_json(response.output_text)
                    validate_observations(result, conversation, checklist)
                    record.update(status="completed", observations=result.model_dump())
                else:
                    result = Evaluation.model_validate_json(response.output_text)
                    validate_evaluation(result, conversation, checklist, require_audit=self.grounded)
                    record.update(status="completed", evaluation=result.model_dump(),
                                  score=calculate_score(result, checklist))
        except APIStatusError as error:
            record["error"] = "api_http_" + str(error.status_code)
            record["api_error_code"] = error.code
            record["api_error_param"] = error.param
            if error.status_code == 429 and error.code in {"credit_balance_exhausted", "insufficient_quota"}:
                self.provider_blocked = True
                record["billing_state"] = "provider_rejected"
                record["settled_cost_usd"] = 0
        except APIConnectionError:
            record["error"] = "api_connection_or_timeout"
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            # Validation errors can include source text. Store only our controlled error label.
            record["error"] = "invalid_evaluation_" + type(error).__name__
            if isinstance(error, ValueError) and not isinstance(error, ValidationError):
                record["validation_reason"] = str(error)
        finally:
            record["latency_seconds"] = round(perf_counter() - started, 3)
            usage = record["usage"]
            self.ledger.finish(call_id, record["status"],
                               cost=usage["estimated_cost_usd"] if usage else record.get("settled_cost_usd"),
                               input_tokens=usage["input_tokens"] if usage else None,
                               output_tokens=usage["output_tokens"] if usage else None)
        return record


def schema_for(conversation: Conversation, checklist: Checklist, *, grounded=False):
    """Constrain references and IDs mechanically without hardcoding criterion meaning."""
    schema = Evaluation.model_json_schema()
    message_ids = [m.id for m in conversation.messages]
    definitions = schema["$defs"]
    schema["required"] = list(schema["properties"])
    for definition in definitions.values():
        if definition.get("type") == "object":
            definition["required"] = list(definition["properties"])
    definitions["Evidence"]["properties"]["message_id"]["enum"] = message_ids
    judgment = definitions["Judgment"]["properties"]
    judgment["criterion_id"]["enum"] = [c.id for c in checklist.criteria]
    judgment["checked_message_ids"]["items"]["enum"] = message_ids
    if grounded:
        deduction = definitions["Deduction"]["properties"]
        deduction["criterion_id"]["enum"] = [c.id for c in checklist.criteria]
        deduction["checked_message_ids"]["items"]["enum"] = message_ids
        definitions["FactualClaim"]["properties"]["criterion_ids"]["items"]["enum"] = [c.id for c in checklist.criteria]
        if conversation.references:
            definitions["ReferenceEvidence"]["properties"]["reference_id"]["enum"] = [r.id for r in conversation.references]
    else:
        for field in ["deductions", "factual_claims"]:
            schema["properties"].pop(field)
            schema["required"].remove(field)
        for name in ["Deduction", "FactualClaim", "ReferenceEvidence"]:
            definitions.pop(name)
    values = sorted({level.value for c in checklist.criteria for level in c.levels})
    for option in judgment["answer"]["anyOf"]:
        if option.get("type") == "string":
            option["enum"] = values
    coverage_definition = definitions["RequestCoverage"]
    coverage = coverage_definition["properties"]
    # Strict API schema requires every property; historical records may omit the new field.
    coverage_definition["required"] = list(coverage)
    for field, role in [("request_message_ids", "client"), ("answer_message_ids", "operator"),
                        ("withdrawal_message_ids", "client")]:
        ids = [m.id for m in conversation.messages if m.speaker == role]
        if ids:
            coverage[field]["items"]["enum"] = ids
    return schema
