from scripts.report_calibrated_benchmark import decision_statistics


def test_uncertain_references_do_not_inflate_scored_agreement_and_failures_remain():
    labels = [{"case_id": "example", "criterion_id": cid, "expected_status": status,
               "expected_answer": answer, "provenance": "assistant_only", "reference_caveat": None}
              for cid, status, answer in [("unknown", "needs_review", None), ("known", "scored", "yes")]]
    rows = [{"case_id": "example", "record": {"status": "failed"},
             "comparison": {"total_absolute_error": None, "checks": [
                 {"criterion_id": label["criterion_id"], "expected_status": label["expected_status"],
                  "expected_answer": label["expected_answer"], "matched": False,
                  "actual_status": None, "actual_answer": None} for label in labels]}}]
    summary = decision_statistics(rows, labels)
    assert summary["determinate_reference_checks"] == 1
    assert summary["provisional_label_agreement"] == 0
    assert len(summary["uncertain_reference_dispositions"]) == 1
    assert summary["statuses"] == {"failed": 1}
