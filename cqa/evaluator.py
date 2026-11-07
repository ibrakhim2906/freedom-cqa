import hashlib
import json
from time import perf_counter

from openai import APIConnectionError, APIStatusError, AsyncOpenAI
from pydantic import ValidationError

from .ledger import Ledger
from .models import Checklist, Conversation, Evaluation
from .prompt import PROMPT_VERSION, SYSTEM, fingerprint, payload_for
from .scoring import calculate_score, validate_evaluation
from .settings import RATES, Settings


class Evaluator:
    def __init__(self, settings: Settings, ledger: Ledger, run_ceiling: float):
        settings.require_key()
        self.settings, self.ledger, self.run_ceiling = settings, ledger, run_ceiling
        # No invisible SDK retries: each billable attempt is reserved and recorded here.
        self.client = AsyncOpenAI(api_key=settings.api_key, max_retries=0, timeout=settings.timeout)

    async def close(self):
        await self.client.close()

    async def evaluate(self, conversation: Conversation, checklist: Checklist):
        payload = payload_for(conversation, checklist)
        schema = Evaluation.model_json_schema()
        input_rate, output_rate = RATES[self.settings.model]
        # UTF-8 byte count plus schema and framing allowance is a conservative token bound.
        input_bound = len((SYSTEM + payload + json.dumps(schema)).encode("utf-8")) + 4096
        if input_bound > 200_000:
            raise ValueError("Input exceeds this benchmark's short-context cost bound")
        reservation = (input_bound * input_rate + self.settings.max_output_tokens * output_rate) / 1_000_000
        call_id = self.ledger.reserve(self.settings.model, reservation, self.run_ceiling)
        started = perf_counter()
        record = {"status": "failed", "conversation_id": conversation.id,
                  "input_fingerprint": fingerprint(conversation, checklist),
                  "checklist_hash": hashlib.sha256(checklist.model_dump_json().encode()).hexdigest(),
                  "checklist_id": checklist.id, "checklist_version": checklist.version,
                  "prompt_version": PROMPT_VERSION, "model": self.settings.model,
                  "reasoning_effort": self.settings.effort, "ledger_call_id": call_id,
                  "reserved_usd": round(reservation, 6), "audio_analyzed": False,
                  "evaluation": None, "score": None, "error": None, "usage": None}
        try:
            response = await self.client.responses.create(
                model=self.settings.model, instructions=SYSTEM, input=payload,
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
