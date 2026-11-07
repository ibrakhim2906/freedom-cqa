"""Explicitly authored offline fixtures; never a runtime encoder or repair path.

The serializer below selects exact already-authored source strings. It cannot
invent claim IDs, proof premises, dependencies, grades, quote spelling or missing
metadata. Historical records are never passed through it by application code.
"""

from copy import deepcopy

from cqa.models import Checklist, Conversation
from cqa.source_spans import build_catalog


def premise(pid, *, evidence=(), references=(), rules=(), proposition=None):
    return {"premise_id": pid, "proposition": proposition, "evidence": list(evidence),
            "reference_evidence": list(references), "rule_evidence": list(rules),
            "depends_on_claim_id": None, "required_status": None}


def proof(*premises):
    return {"relation": "direct" if len(premises) == 1 else "all_of", "premises": list(premises),
            "required_premise_ids": [p["premise_id"] for p in premises],
            "explanation": "The explicitly listed source premises establish the stated canonical proposition."}


def wire_for(data, conversation, checklist, *, contract="span-v4"):
    """Serialize an authored fixture for an explicit wire version, never inference."""
    data = deepcopy(data)
    assert contract in {"span-v3", "span-v4"}
    assert data["semantic_audit"]["version"] in {"coverage-v3", "coverage-v4"}
    data["semantic_audit"]["version"] = "coverage-v4" if contract == "span-v4" else "coverage-v3"
    assert data["assertion_groups"] is not None
    catalog = build_catalog(conversation, checklist)
    indexed = {claim["claim_id"]: claim for claim in data["factual_claims"]}
    assert None not in indexed and len(indexed) == len(data["factual_claims"])

    def leaf_sources(cid, seen=()):
        assert cid not in seen and cid in indexed
        result = {field: set() for field in ["evidence", "reference_evidence", "rule_evidence"]}
        claim_proof = indexed[cid]["proof"]
        if claim_proof is None:
            return result
        for item in claim_proof["premises"]:
            if item["depends_on_claim_id"] is not None:
                inherited = leaf_sources(item["depends_on_claim_id"], (*seen, cid))
                for field, selected in result.items():
                    selected.update(inherited[field])
            else:
                for field, selected in result.items():
                    owner = {"evidence": "message_id", "reference_evidence": "reference_id", "rule_evidence": "criterion_id"}[field]
                    selected.update((source[owner], source["quote"]) for source in item[field])
        return result

    roles = {m.id: m.speaker for m in conversation.messages}
    for claim in data["factual_claims"]:
        leaves = leaf_sources(claim["claim_id"])
        for field, flat in [("evidence", "dialogue_evidence"), ("reference_evidence", "reference_evidence"),
                            ("rule_evidence", "rule_evidence")]:
            owner = {"evidence": "message_id", "reference_evidence": "reference_id", "rule_evidence": "criterion_id"}[field]
            declared = [(item[owner], item["quote"]) for item in claim[flat]]
            expected = leaves[field]
            if field == "evidence":
                expected = {item for item in expected if roles[item[0]] != "operator"}
            assert len(declared) == len(set(declared)) and set(declared) == expected, (
                "Fixture flat fields must already equal their explicit proof source union; serializer cannot repair them")

    def select(value):
        key = next(k for k in ["message_id", "reference_id", "criterion_id"] if k in value)
        kind = {"message_id": "dialogue", "reference_id": "reference", "criterion_id": "rule"}[key]
        matches = [s.span_id for s in catalog.entries.values()
                   if s.kind == kind and s.source_id == value[key] and s.quote == value["quote"]]
        assert matches, f"Fixture must explicitly choose a catalog source, not a repaired quote: {value!r}"
        return {"span_id": matches[0]}

    def convert(value, owner=None):
        if isinstance(value, list):
            return [convert(x, owner) for x in value]
        if not isinstance(value, dict):
            return value
        if "quote" in value:
            assert set(value) in [{"message_id", "quote"}, {"reference_id", "quote"}, {"criterion_id", "quote"}]
            return select(value)
        owner = value.get("criterion_id", owner)
        result = {}
        for key, item in value.items():
            if key == "rule_quote":
                result["rule_span_id"] = select({"criterion_id": owner, "quote": item})["span_id"]
            elif key == "source_citations":
                assert item is None
            else:
                result[key] = convert(item, owner)
        return result

    audits = {d["criterion_id"]: d for d in data.pop("deductions")}
    data["judgments"] = {j["criterion_id"]: {**j, "deduction": audits.get(j["criterion_id"])}
                         for j in data["judgments"]}
    for claim in data["factual_claims"]:
        assert claim["claim_id"] and claim["assertion_group_id"] and "proof" in claim
        for impact in claim["assessment"]["impacts"]:
            assert impact["fixed_claim_ids"] is not None
        if claim["dialogue_evidence"]:
            assert claim["supported_proposition"] == claim["claim"]
            observation = {"target": "claim", "scope": claim["observation_scope"]}
        else:
            assert claim["observation_scope"] == "none"
            assert claim["supported_proposition"] is None or claim["verification_scope"] == "commitment"
            observation = None
        for field in ["dialogue_evidence", "reference_evidence", "rule_evidence", "observation_scope", "supported_proposition"]:
            claim.pop(field)
        claim["observation"] = observation
        if claim["proof"]:
            for item in claim["proof"]["premises"]:
                if item["depends_on_claim_id"] is not None:
                    assert not item["evidence"] and not item["reference_evidence"] and not item["rule_evidence"]
                    for field in ["evidence", "reference_evidence", "rule_evidence"]:
                        item[field] = None
                elif contract == "span-v4" and observation is None and claim["verification_scope"] != "commitment":
                    assert not item["evidence"], "A fixture cannot hide independent proof under observation=null"
                    item["evidence"] = None
    if contract == "span-v4":
        for group in data["assertion_groups"]:
            group.pop("operator_evidence")
    for request in data["request_coverage"]:
        status, support = request["status"], request["support"]
        if status != "withdrawn":
            assert request["withdrawal_message_ids"] == []
            request["withdrawal_message_ids"] = None
        if status in {"withdrawn", "unanswered"}:
            assert request["answer_message_ids"] == []
            request["answer_message_ids"] = None
        if status not in {"partial", "unanswered"}:
            assert support["unresolved_aspects"] == []
            support["unresolved_aspects"] = None
        if status == "unanswered":
            assert support["evidence"] == []
            support["evidence"] = None
    # The no-reference branch explicitly declares forbidden citation collections
    # null. This is serialization of absence already authored in the fixture.
    def absent_reference_collections(value):
        if isinstance(value, list):
            for item in value:
                absent_reference_collections(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key == "reference_evidence" and not conversation.references:
                    assert item in [[], None]
                    value[key] = None
                else:
                    absent_reference_collections(item)
    absent_reference_collections(data)
    data = convert(data)
    data["contract_version"] = contract
    data["catalog_fingerprint"] = catalog.fingerprint
    return data


def novel_fixture():
    """New custom rubric with correction, mixed truth, observation and omission."""
    conversation = Conversation.model_validate({"id": "unseen-span-workflow", "channel": "agent chat", "language": "EN",
        "knowledge_scope": "sample-lab", "occurred_on": "2026-11-07", "messages": [
            {"id": "q", "timestamp": "11:00", "speaker": "client",
             "text": "Help me download the sample PDF and tell me when edits take effect."},
            {"id": "first", "timestamp": "11:01", "speaker": "operator",
             "text": "Hello, I'm Nia. Click Download and open sample.pdf. Edits apply immediately without review. Holds must be announced before they begin."},
            {"id": "done", "timestamp": "11:02", "speaker": "client",
             "text": "I clicked Download and opened sample.pdf 👩🏽‍💻. Does the guide give a deadline?"},
            {"id": "held", "timestamp": "11:03", "speaker": "system", "text": "The operator placed this chat on hold."},
            {"id": "back", "timestamp": "11:04", "speaker": "system", "text": "The operator resumed this chat."},
            {"id": "fixed", "timestamp": "11:05", "speaker": "operator",
             "text": "Correction: submitting an edit sends it for review; execution follows review. You downloaded and opened the sample PDF."},
            {"id": "no-use", "timestamp": "11:06", "speaker": "client", "text": "I did not rely on the immediate-execution statement."},
            {"id": "bye", "timestamp": "11:07", "speaker": "operator", "text": "Goodbye."}],
        "references": [{"id": "lab-instruction", "text": "Submitting an edit sends it for review; execution follows review.",
            "provenance": "Explicit fictional lab guide, not a broker policy", "scope": "sample-lab",
            "valid_from": "2026-11-07", "valid_until": "2026-11-07"}]})
    checklist = Checklist.model_validate({"id": "custom-source-review", "version": "1", "title": "Sample lab assessment",
        "instructions": [], "criteria": [
            {"id": "resolution", "title": "Resolve requests", "instruction": "Resolve every request; judge corrected final advice while preserving unresolved requests.",
             "kind": "scale", "weight": 60, "na_condition": None,
             "levels": [{"value": "20", "fraction": 1, "description": "All requests resolved."},
                        {"value": "10", "fraction": .5, "description": "One substantive request remains unanswered."},
                        {"value": "0", "fraction": 0, "description": "Active wrong key advice."}], "channel_guidance": {}},
            {"id": "process", "title": "Announce holds", "instruction": "Holds must be announced before they begin.",
             "kind": "binary", "weight": 25, "na_condition": None,
             "levels": [{"value": "yes", "fraction": 1, "description": "Every hold was announced."},
                        {"value": "no", "fraction": 0, "description": "An unannounced hold occurred."}], "channel_guidance": {}},
            {"id": "closing", "title": "Close", "instruction": "Finish with a further-help offer and farewell.",
             "kind": "binary", "weight": 15, "na_condition": None,
             "levels": [{"value": "yes", "fraction": 1, "description": "The closing contains both required actions."},
                        {"value": "no", "fraction": 0, "description": "The closing omits a required action."}], "channel_guidance": {}}]})
    mids = [m.id for m in conversation.messages]
    messages = {m.id: m.text for m in conversation.messages}
    ev = lambda mid: {"message_id": mid, "quote": messages[mid]}
    ref = {"reference_id": "lab-instruction", "quote": conversation.references[0].text}
    rule = {"criterion_id": "process", "quote": checklist.criteria[1].instruction}
    judgments = [{"criterion_id": cid, "status": "scored", "answer": answer, "explanation": explanation,
        "evidence": [ev(mid)], "counterevidence": [], "checked_message_ids": mids, "uncertainty": None}
        for cid, answer, mid, explanation in [
            ("resolution", "10", "done", "The download and corrected execution guidance are resolved; the guide deadline question is not answered."),
            ("process", "no", "held", "The actual hold was unannounced; this is independent of the consultation omission."),
            ("closing", "no", "bye", "Only a farewell was given, without the required offer.")]]

    def impact(cid, fixed=(), false=None):
        j = next(j for j in judgments if j["criterion_id"] == cid)
        outcome = {"status": "scored", "answer": j["answer"]}
        return {"criterion_id": cid, "when_true": outcome,
                "when_false": {"status": "scored", "answer": false} if false else outcome,
                "rule_quote": next(c.instruction for c in checklist.criteria if c.id == cid),
                "evidence": [ev("first"), ev("fixed")], "checked_message_ids": mids,
                "explanation": "Other listed claims remain fixed, including the unresolved deadline and actual correction.",
                "fixed_claim_ids": list(fixed)}

    def claim(cid, group, text, operator, criteria, kind, scope, sources, claim_proof, assessment, dialogue=()):
        return {"claim": text, "claim_id": cid, "assertion_group_id": group, "criterion_ids": criteria,
            "operator_evidence": [ev(operator)], "status": "supported", "material": True,
            "reference_evidence": sources, "dialogue_evidence": list(dialogue), "rule_evidence": [],
            "context_evidence": [], "explanation": "Explicit authored source/proof fixture, not a provider result.",
            "assessment": assessment, "evidence_kind": kind, "verification_scope": scope,
            "observation_scope": "task_completed" if dialogue else "none",
            "supported_proposition": text if dialogue else None, "proof": claim_proof}

    original = claim("original", "first-group", "Edits apply immediately without review.", "first", ["resolution"],
        "product_fact", "policy", [ref], proof(premise("guide", references=[ref])),
        {"lifecycle": "corrected", "correction": {"operator_evidence": [ev("fixed")], "outcome_evidence": [ev("no-use")],
            "reference_evidence": [ref], "remaining_consequence": "none_established",
            "explanation": "The explicit correction is source-backed and the client reports no reliance."},
         "impacts": [impact("resolution", ["review", "download"])]})
    original["status"] = "contradicted"
    norm = claim("hold-rule", "first-group", "Holds must be announced before they begin.", "first", ["process"],
        "grading_rule", "grading_rule", [], proof(premise("rule", rules=[rule])),
        {"lifecycle": "active", "correction": None, "impacts": [impact("process")]})
    norm["rule_evidence"] = [rule]
    review = claim("review", "final-group", "Edits execute after review.", "fixed", ["resolution"],
        "product_fact", "policy", [ref], proof(premise("guide", references=[ref])),
        {"lifecycle": "active", "correction": None, "impacts": [impact("resolution", ["original", "download"], "0")]})
    downloaded = claim("download", "final-group", "The sample PDF was downloaded and opened.", "fixed", ["resolution"],
        "general_fact", "interaction", [], proof(premise("outcome", evidence=[ev("done")])),
        {"lifecycle": "active", "correction": None, "impacts": [impact("resolution", ["original", "review"])]}, [ev("done")])
    downloaded["context_evidence"] = [ev("no-use")]
    requests = []
    for question, req_ids, answers, status, unresolved in [
        ("Download/open the sample PDF and explain execution timing.", ["q"], ["first", "fixed"], "answered", []),
        ("Whether the guide gives a deadline.", ["done"], [], "unanswered", ["A guide deadline or a grounded statement that none is supplied."])]:
        requests.append({"request": question, "request_message_ids": req_ids, "status": status,
            "answer_message_ids": answers, "withdrawal_message_ids": [], "explanation": "Explicit fixture coverage.",
            "support": {"basis": "explicit" if answers else "none", "evidence": [ev(m) for m in answers], "inference": None,
                "unresolved_aspects": unresolved, "omission": None if answers else {
                    "start_message_id": "done", "end_message_id": "bye", "context_evidence": [ev("done"), ev("held"), ev("bye")]}}})
    data = {"judgments": judgments, "request_coverage": requests, "scope_notes": ["Novel authored test; no policy inference from context."],
        "factual_claims": [original, norm, review, downloaded],
        "deductions": [{"criterion_id": j["criterion_id"], "rule_quote": next(c.instruction for c in checklist.criteria if c.id == j["criterion_id"]),
            "defect": j["explanation"], "evidence": j["evidence"], "checked_message_ids": mids,
            "overlap_note": "Independent omission/hold/closing defects remain separately evidenced."} for j in judgments],
        "semantic_audit": {"version": "coverage-v3", "reviewed_message_ids": [m.id for m in conversation.messages if m.speaker in {"client", "operator"}],
            "exclusions": [{"evidence": ev("no-use"), "reason": "context_or_confirmation", "criterion_ids": ["resolution"],
                "explanation": "Client non-use informs the correction consequence, not policy truth."},
                {"evidence": ev("bye"), "reason": "criterion_behavior", "criterion_ids": ["closing"], "explanation": "Bare farewell is assessed under closing."}]},
        "assertion_groups": [{"group_id": "first-group", "composition": "all_of", "operator_evidence": [ev("first")], "claim_ids": ["original", "hold-rule"]},
            {"group_id": "final-group", "composition": "all_of", "operator_evidence": [ev("fixed")], "claim_ids": ["review", "download"]}],
        "source_citations": None}
    return conversation, checklist, data


def explicit_browser_fixture(conversation, checklist, old_wire):
    """Authored v3 mock of the older identity-audit scenario, not a result migration.

    Full immutable sources are deliberately selected here. Three atom IDs,
    memberships and fixed-claim sets are authored for these known fixture facts;
    neither this function nor the serializer is used by application code.
    """
    data = deepcopy(old_wire)
    inline = data["judgments"]
    data["deductions"] = [j.pop("deduction") for j in inline.values() if j.get("deduction") is not None]
    for judgment in inline.values():
        judgment.pop("deduction", None)
    data["judgments"] = list(inline.values())
    messages = {m.id: m.text for m in conversation.messages}
    refs = {r.id: r.text for r in conversation.references}
    rules = {c.id: c.instruction for c in checklist.criteria}

    def authored_full_sources(value, owner=None):
        if isinstance(value, list):
            values = [authored_full_sources(x, owner) for x in value]
            if values and all(isinstance(x, dict) and "quote" in x for x in values):
                unique = []
                for item in values:
                    if item not in unique:
                        unique.append(item)
                return unique
            return values
        if not isinstance(value, dict):
            return value
        owner = value.get("criterion_id", owner)
        if "quote" in value:
            if "message_id" in value:
                return {"message_id": value["message_id"], "quote": messages[value["message_id"]]}
            if "reference_id" in value:
                return {"reference_id": value["reference_id"], "quote": refs[value["reference_id"]]}
            return {"criterion_id": value["criterion_id"], "quote": rules[value["criterion_id"]]}
        return {key: rules[owner] if key == "rule_quote" else authored_full_sources(item, owner)
                for key, item in value.items()}

    data = authored_full_sources(data)
    data["semantic_audit"]["version"] = "coverage-v3"
    data["source_citations"] = None
    data["assertion_groups"] = []
    ids = ["identity-requirement", "private-status", "report-route"]
    for index, claim in enumerate(data["factual_claims"]):
        claim["claim_id"] = ids[index]
        claim["assertion_group_id"] = "browser-group-" + str(index)
        if index == 2:
            # The saved reference proves the route. Client download confirms an
            # outcome, not this general policy proposition; keep it as context.
            claim["context_evidence"] += claim["dialogue_evidence"]
            claim["dialogue_evidence"] = []
            claim["observation_scope"] = "none"
            claim["supported_proposition"] = None
            claim["verification_scope"] = "policy"
        claim["proof"] = proof(premise("source", evidence=claim["dialogue_evidence"],
                                        references=claim["reference_evidence"], rules=claim["rule_evidence"]))
        data["assertion_groups"].append({"group_id": claim["assertion_group_id"], "composition": "atomic",
            "operator_evidence": deepcopy(claim["operator_evidence"]), "claim_ids": [claim["claim_id"]]})
        for impact in claim["assessment"]["impacts"]:
            impact["fixed_claim_ids"] = [ids[n] for n, other in enumerate(data["factual_claims"])
                if n != index and impact["criterion_id"] in other["criterion_ids"]]
    return data


def dependent_fixture():
    """A private classification and policy jointly establish account eligibility."""
    conversation = Conversation.model_validate({"id": "unseen-dependent-proof", "channel": "agent chat", "language": "EN",
        "knowledge_scope": "fictional-broker", "occurred_on": "2026-11-07", "messages": [
            {"id": "q", "timestamp": "11:00", "speaker": "client", "text": "For my verified account A, confirm its classification and route-X eligibility."},
            {"id": "verified", "timestamp": "11:01", "speaker": "system", "text": "Identity verification confirmed for account A."},
            {"id": "a", "timestamp": "11:02", "speaker": "operator", "text": "Hello, I'm Bo. Account A is retail, so route X is allowed."},
            {"id": "thanks", "timestamp": "11:03", "speaker": "client", "text": "Thank you."},
            {"id": "bye", "timestamp": "11:04", "speaker": "operator", "text": "Please contact us for further help. Goodbye."}],
        "references": [{"id": rid, "text": text, "provenance": "Explicit fictional fixture, not actual broker policy",
            "scope": "fictional-broker", "valid_from": "2026-11-07", "valid_until": "2026-11-07"}
            for rid, text in [("private-classification", "Private session record: account A is retail."),
                              ("route-policy", "Retail accounts are allowed to use route X.")]]})
    checklist = Checklist.model_validate({"id": "eligibility-review", "version": "1", "title": "Classification and eligibility",
        "instructions": [], "criteria": [{"id": cid, "title": cid, "instruction": text, "kind": "binary", "weight": 50,
            "levels": [{"value": "yes", "fraction": 1, "description": "The requested fact is correct."},
                       {"value": "no", "fraction": 0, "description": "The requested fact is false."}],
            "na_condition": None, "channel_guidance": {}} for cid, text in [
                ("classification", "Correctly state the verified account classification."),
                ("eligibility", "Establish eligibility from both the account classification and the applicable policy.")]]})
    ev = lambda mid: {"message_id": mid, "quote": next(m.text for m in conversation.messages if m.id == mid)}
    references = [{"reference_id": r.id, "quote": r.text} for r in conversation.references]
    claims = []
    for index, (cid, text) in enumerate([("class", "Account A is retail."), ("eligible", "Account A is eligible for route X.")]):
        criterion = checklist.criteria[index]
        leaves = references[:1] if index == 0 else references
        claim_proof = proof(premise("record", references=references[:1])) if index == 0 else proof(
            {"premise_id": "classification", "proposition": None, "evidence": [], "reference_evidence": [],
                "rule_evidence": [], "depends_on_claim_id": "class", "required_status": "supported"},
            premise("policy", references=references[1:], proposition="Retail accounts are allowed to use route X."))
        claims.append({"claim": text, "claim_id": cid, "assertion_group_id": "joint", "criterion_ids": [criterion.id],
            "operator_evidence": [ev("a")], "status": "supported", "material": True,
            "reference_evidence": leaves, "dialogue_evidence": [], "rule_evidence": [], "context_evidence": [],
            "observation_scope": "none", "supported_proposition": None, "verification_scope": "private_record",
            "evidence_kind": "account_state", "explanation": "The private record and applicable policy concern the same verified account.",
            "assessment": {"lifecycle": "active", "correction": None, "impacts": [{"criterion_id": criterion.id,
                "when_true": {"status": "scored", "answer": "yes"}, "when_false": {"status": "scored", "answer": "no"},
                "fixed_claim_ids": [], "rule_quote": criterion.instruction, "evidence": [ev("q"), ev("a")],
                "checked_message_ids": [m.id for m in conversation.messages], "explanation": "The separately configured criterion assesses this canonical proposition."}]},
            "proof": claim_proof})
    data = {"judgments": [{"criterion_id": criterion.id, "status": "scored", "answer": "yes",
        "explanation": "Both the record and route policy support the stated result.", "evidence": [ev("a")],
        "counterevidence": [], "checked_message_ids": [m.id for m in conversation.messages], "uncertainty": None}
        for criterion in checklist.criteria], "request_coverage": [{"request": "Confirm classification and eligibility.",
        "request_message_ids": ["q"], "status": "answered", "answer_message_ids": ["a"], "withdrawal_message_ids": [],
        "explanation": "The operator explicitly answers both parts.", "support": {"basis": "explicit", "evidence": [ev("a")],
            "inference": None, "unresolved_aspects": [], "omission": None}}], "scope_notes": [], "factual_claims": claims,
        "deductions": [], "assertion_groups": [{"group_id": "joint", "composition": "all_of", "operator_evidence": [ev("a")], "claim_ids": ["class", "eligible"]}],
        "semantic_audit": {"version": "coverage-v3", "reviewed_message_ids": ["q", "a", "thanks", "bye"],
            "exclusions": [{"evidence": ev(mid), "reason": "social", "criterion_ids": [], "explanation": "Social acknowledgment or farewell, not additional factual advice."}
                           for mid in ["thanks", "bye"]]}, "source_citations": None}
    return conversation, checklist, data
