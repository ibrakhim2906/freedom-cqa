from decimal import ROUND_HALF_UP, Decimal
from itertools import product
from random import Random

from cqa.models import Checklist, Criterion, Evaluation, Judgment, Level
from cqa.scoring import calculate_score


def make_case(spec):
    criteria, judgments = [], []
    for i, (weight, fractions, optional, answer) in enumerate(spec):
        cid = f"new-{i}"
        criteria.append(Criterion(id=cid, title=cid, instruction="Custom tiers", kind="scale", weight=weight,
            levels=[Level(value=str(j), fraction=f, description="Tier") for j, f in enumerate(fractions)],
            na_condition="Only when no applicable event occurred" if optional else None))
        judgments.append(Judgment(criterion_id=cid, status="needs_review" if answer is None else "scored",
            answer=None if answer is None else str(answer), explanation="Source uncertain", evidence=[],
            counterevidence=[], checked_message_ids=["m1"], uncertainty="Ambiguous source" if answer is None else None))
    return (Evaluation(judgments=judgments, request_coverage=[], scope_notes=[]),
            Checklist(id="new", version="1", title="New", instructions=[], criteria=criteria))


def test_closing_uncertainty_has_bounds_without_inventing_a_total():
    result, checklist = make_case([(60, [0, 1], False, 1), (5, [0, 1], True, None)])
    score = calculate_score(result, checklist)
    assert score["total"] is None and score["provisional"]
    assert score["score_bounds"]["lower"] == 92.31
    assert score["score_bounds"]["upper"] == 100
    assert not score["score_bounds"]["no_numeric_score_possible"]


def test_bounds_match_exhaustive_allowed_assignments_for_arbitrary_rubrics():
    random = Random(901)
    for _ in range(100):
        spec = [(random.choice([0, 1, 3, 7]), random.choice([[0, .5, 1], [.2, .7], [1]]),
                 random.choice([True, False]), None) for _ in range(4)]
        result, checklist = make_case(spec)
        bounds = calculate_score(result, checklist)["score_bounds"]
        options = [fractions + ([None] if optional else []) for _, fractions, optional, _ in spec]
        totals, no_numeric = [], False
        for assignment in product(*options):
            points, weight = Decimal(0), Decimal(0)
            for (w, _, _, _), fraction in zip(spec, assignment, strict=True):
                if fraction is not None:
                    weight += Decimal(str(w))
                    points += Decimal(str(w)) * Decimal(str(fraction))
            if weight:
                totals.append(float((100 * points / weight).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)))
            else:
                no_numeric = True
        assert bounds["lower"] == (min(totals) if totals else None)
        assert bounds["upper"] == (max(totals) if totals else None)
        assert bounds["no_numeric_score_possible"] == no_numeric


def test_final_scores_have_collapsed_bounds_and_all_na_has_none():
    result, checklist = make_case([(3, [.2, 1], True, 0)])
    score = calculate_score(result, checklist)
    assert score["total"] == score["score_bounds"]["lower"] == score["score_bounds"]["upper"] == 20
    result.judgments[0].status, result.judgments[0].answer = "not_applicable", None
    score = calculate_score(result, checklist)
    assert score["total"] is None
    assert score["score_bounds"]["lower"] is score["score_bounds"]["upper"] is None
    assert score["score_bounds"]["no_numeric_score_possible"]
