"""A changed decision must survive orchestration and the saved effective result."""

import asyncio
from copy import deepcopy

from test_assessor import source, wire_for  # noqa: F401 -- shared pytest fixture

from backend.service import effective_result
from cqa.assessor import validate_native
from cqa.evaluator import Evaluator
from cqa.scoring import calculate_score


def test_confident_pass_disagreement_survives_final_composition(source, monkeypatch):  # noqa: F811
    conversation, checklist = source
    first = wire_for(*source)
    corrected = deepcopy(first)
    corrected['judgments']['hello/custom'].update(
        answer='absent', explanation='Synthetic orchestration fixture: revised decision.')

    def record(wire, response_id):
        parsed = validate_native(wire, conversation, checklist)
        return {'status': 'completed', 'assessment': parsed.native,
                'evaluation': parsed.evaluation.model_dump(),
                'score': calculate_score(parsed.evaluation, checklist),
                'response_id': response_id, 'raw_output_text': 'synthetic fixture',
                'latency_seconds': 0, 'usage': None}

    # Even a future priority selector must not hide a second-pass disagreement.
    monkeypatch.setattr('cqa.assessor_challenge.select_review_criteria', lambda *args: ['help'])
    stages = []
    evaluator = Evaluator.__new__(Evaluator)
    evaluator.strategy = 'assessor-reviewed'

    async def stage(*args, stage='grading', observations=None):
        stages.append((stage, observations))
        return [record(first if stage == 'grading' else corrected, stage)]

    evaluator._stage = stage
    final = asyncio.run(evaluator._assess_with_review(conversation, checklist))
    assert final['review']['disagreements'] == ['hello/custom']
    assert final['review']['changed_criteria'] == ['hello/custom']
    assert stages[-1][1]['ids'] == ['hello/custom']
    assert final['response_id'] is None
    assert final['assessment_provenance']['criterion_response_ids']['hello/custom'] == 'adjudication'
    assert final['primary_assessment']['transport']['judgments']['hello/custom']['answer'] == 'present'
    # Verify the same projection consumed by the API/UI and full result export.
    from types import SimpleNamespace

    effective = effective_result(SimpleNamespace(record=final, status='completed'), checklist, [])
    judgments = {j['criterion_id']: j for j in effective['judgments']}
    assert judgments['hello/custom']['answer'] == 'absent'
    assert judgments['help']['answer'] == 'done'
    assert effective['score']['total'] == 66.67
