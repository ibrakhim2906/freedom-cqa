"""Explicit FBroker import preset; no inference, stored answers or source rewriting."""
import json

from cqa.grounding import evidence_context_for, select_reference_context
from cqa.settings import ROOT

SCOPE = "freedom-finance-global-platform"
AS_OF = "2026-11-07"
RATIONALE = (
    "The user authorized the team to choose the policy context and numerically assess each "
    "conversation from available evidence with stated assumptions. Assume the Freedom Finance "
    "Global platform policy snapshot as of 2026-11-07 for this assessment. This conditional "
    "choice does not establish the actual broker, conversation date, historical applicability, "
    "or private account state. Preserve uncertainty about facts the supplied sources do not establish."
)


def apply_fbroker_preset(content, parsed):
    payload = json.loads(content.lstrip("\ufeff"))
    payload = payload if isinstance(payload, dict) else {}
    envelope = payload.get("data", payload)
    groups = [payload.get("dataset_group_id")]
    if isinstance(envelope, dict):
        groups.append(envelope.get("dataset_group_id"))
    groups = [str(group).strip().casefold() for group in groups if group is not None]
    if not groups or any(group != "fbroker" for group in groups):
        raise ValueError("FBroker: набор должен быть помечен FBroker. Для SWAP и других файлов используйте обычную загрузку.")
    pack = ROOT / "references/freedom-global-products-20261107.json"
    prepared = []
    for conversation, extra in parsed:
        if conversation.reference_context is not None:
            raise ValueError("FBroker: уже выбранные условия проверки сохраняются; измените их вручную в диалоге.")
        revised = select_reference_context(conversation, pack, SCOPE,
            mode="snapshot_review", as_of=AS_OF, rationale=RATIONALE)
        context = evidence_context_for(revised)
        if len(context["references"]) < 9 or sum(ref["usable"] for ref in context["references"]) < 9:
            raise ValueError("FBroker: не удалось подключить девять справочных документов.")
        prepared.append((revised, extra))
    return prepared
