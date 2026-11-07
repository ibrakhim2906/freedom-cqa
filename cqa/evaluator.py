import hashlib
import json
from time import perf_counter

from openai import APIConnectionError, APIStatusError, AsyncOpenAI
from pydantic import ValidationError

from .ledger import BudgetExceeded, Ledger
from .models import Checklist, Conversation, Evaluation
from .prompt import PROMPT_VERSION, SYSTEM, fingerprint, payload_for
from .scoring import calculate_score, validate_evaluation
from .settings import RATES, Settings


class Evaluator:
    def __init__(self, settings: Settings, ledger: Ledger, run_ceiling: float):
        settings.require_key()
        self.settings, self.ledger, self.run_ceiling = settings, ledger, run_ceiling
        # No invisible SDK retries: each billable attempt is reserved and recorded here.
        self.client = AsyncOpenAI(api_key=settings.api_key, base_url="https://api.openai.com/v1",
                                  max_retries=0, timeout=settings.timeout)

    async def close(self):
        await self.client.close()

    async def evaluate(self, conversation: Conversation, checklist: Checklist):
        attempts = []
        feedback = None
        for _ in range(2):
            try:
                record = await self._attempt(conversation, checklist, feedback)
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
        final = dict(attempts[-1])
        final["attempt_records"] = attempts
        final["attempt_count"] = len(attempts)
        final["latency_seconds"] = round(sum(a["latency_seconds"] for a in attempts), 3)
        known_usage = [a["usage"] for a in attempts if a.get("usage")]
        if known_usage:
            final["usage"] = {"input_tokens": sum(a["input_tokens"] for a in known_usage),
                              "output_tokens": sum(a["output_tokens"] for a in known_usage),
                              "estimated_cost_usd": round(sum(a["estimated_cost_usd"] for a in known_usage), 6)}
        return final

    async def _attempt(self, conversation: Conversation, checklist: Checklist, feedback=None):
        payload = payload_for(conversation, checklist)
        schema = schema_for(conversation, checklist)
        instructions = SYSTEM
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
        reservation = (input_bound * input_rate + self.settings.max_output_tokens * output_rate) / 1_000_000
        call_id = self.ledger.reserve(self.settings.model, reservation, self.run_ceiling)
        started = perf_counter()
        record = {"status": "failed", "conversation_id": conversation.id,
                  "input_fingerprint": fingerprint(conversation, checklist),
                  "request_fingerprint": hashlib.sha256((instructions + payload + json.dumps(schema)).encode()).hexdigest(),
                  "checklist_hash": hashlib.sha256(checklist.model_dump_json().encode()).hexdigest(),
                  "checklist_id": checklist.id, "checklist_version": checklist.version,
                  "prompt_version": PROMPT_VERSION, "model": self.settings.model,
                  "reasoning_effort": self.settings.effort, "ledger_call_id": call_id,
                  "reserved_usd": round(reservation, 6), "audio_analyzed": False,
                  "evaluation": None, "score": None, "error": None, "usage": None}
        try:
            response = await self.client.responses.create(
                model=self.settings.model, instructions=instructions, input=payload,
                reasoning={"effort": self.settings.effort}, max_output_tokens=self.settings.max_output_tokens,
                text={"format": {"type": "json_schema", "name": "conversation_evaluation",
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
                result = Evaluation.model_validate_json(response.output_text)
                validate_evaluation(result, conversation, checklist)
                record.update(status="completed", evaluation=result.model_dump(),
                              score=calculate_score(result, checklist))
        except APIStatusError as error:
            record["error"] = "api_http_" + str(error.status_code)
            record["api_error_code"] = error.code
            record["api_error_param"] = error.param
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
                               cost=usage["estimated_cost_usd"] if usage else None,
                               input_tokens=usage["input_tokens"] if usage else None,
                               output_tokens=usage["output_tokens"] if usage else None)
        return record


def schema_for(conversation: Conversation, checklist: Checklist):
    """Constrain references and IDs mechanically without hardcoding criterion meaning."""
    schema = Evaluation.model_json_schema()
    message_ids = [m.id for m in conversation.messages]
    definitions = schema["$defs"]
    definitions["Evidence"]["properties"]["message_id"]["enum"] = message_ids
    judgment = definitions["Judgment"]["properties"]
    judgment["criterion_id"]["enum"] = [c.id for c in checklist.criteria]
    judgment["checked_message_ids"]["items"]["enum"] = message_ids
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
