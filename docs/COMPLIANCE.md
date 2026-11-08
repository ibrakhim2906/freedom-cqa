# Organizer requirements and submission status

Audited against the three supplied PDFs on 8 November 2026. The application,
exporter and existing DEV submission have been checked against the requirements
below. **Final delivery remains incomplete until the actual ten control dialogues
are processed and both result files are committed and pushed before stop-code.**
This document records implementation and delivery evidence; it does not certify
agreement with the organizers' undisclosed reference grades.

The [repository](https://github.com/ibrakhim2906/freedom-cqa) is public, its default
branch is `main`, and the user confirmed that the organizers already have this link.
For a demonstration, use the [five-minute walkthrough](JUDGE_WALKTHROUGH.md).
For source installation, use [README](../README.md) and the
[judge quickstart](JUDGE_QUICKSTART.md).

## Documents reviewed

All pages of each supplied document were extracted and visually inspected. Page
references below identify the source requirement, not an additional team rule.

| Document | Pages | SHA-256 prefix |
|---|---:|---|
| `CQA_Hackathon_Student_Guide_v3 1.pdf` | 4 | `8b2f79a685c67077` |
| `CQA_Chat_Quality_Checklist 1.pdf` | 3 | `2f6908c3026b6221` |
| `CQA_Student_Guide_Appendix_Results.pdf` | 3 | `cf9e282fee6ee6fd` |

The release default is `freedom-reviewed-018`, selected through
[cqa/rubric.py](../cqa/rubric.py) after the complete 14-case comparison and
independent semantic review. All 103 unambiguous configured reference judgments
matched; the ambiguous RU03 closing retained uncertainty and was excluded from
unique-label agreement. All 14 native-source validations and score replays passed.
The additional long call was unlabelled and reviewed qualitatively, with no
accuracy claim. These reused, AI-authored diagnostic references are not fresh
held-out evidence or human Ground Truth. See the
[validation record](../evals/checklist018-validation.results.json) and
[release checklist](RELEASE_CHECKLIST.md).
Saved assessments retain their original checklist and model configuration.
The published DEV results use historical versions 015 and 016; they are not
relabeled as results from a later default.

## Application requirements

| Requirement and PDF reference | Implementation and evidence | Status / boundary |
|---|---|---|
| Configure, add and edit criteria, wording, weights, answer types, scales and N/A; save and apply a changed checklist. Guide pp. 1–2. | [Checklist editor](../frontend/src/Checklists.tsx), [workflow tests](../tests/test_workflow.py), [editor browser test](../frontend/e2e/judge-checklist.spec.ts), [actual model workflow test](../frontend/e2e/release-live.spec.ts). | Implemented. A real two-version custom-rule check produced 100 then 50; this verifies rule application, not general accuracy. Organizer-selected control changes still require their actual demonstration. |
| Import 65 DEV conversations: 60 chats and 5 calls, RU/KZ/EN; preserve IDs, roles, timestamps and recording links. Guide pp. 1, 3. | [Importer](../backend/importing.py), [workflow tests](../tests/test_workflow.py), [recording tests](../tests/test_recording_recovery.py). | Actual DEV composition and IDs verified. `client`, `operator`, `bot` and `system` remain distinct. Failed response envelopes are rejected before saving records. |
| Show each answer, points, weight, rationale, evidence, checked interval for omissions and reason for N/A. Guide p. 2; checklist p. 3. | [Assessment view](../frontend/src/Assessment.tsx), [source contract tests](../tests/test_contract.py), [browser integrity tests](../frontend/e2e/product-integrity.spec.ts). | Implemented. Evidence navigates to saved transcript text; exact-source validation does not itself establish that every explanation is semantically correct. |
| Compute weighted total, exclude N/A weight, round to two decimals, and show serious errors separately. Guide p. 2; checklist pp. 1–2. | [Scorer](../cqa/scoring.py), [submission tests](../tests/test_submission.py), [queue](../frontend/src/ConversationQueue.tsx). | Implemented. “С грубыми ошибками” filters current source revisions by their latest effective official serious flag, not by low score. The badge shows the reason and opens the corresponding saved assessment. Missing or failed assessments are not cleared flags. |
| Submit an appeal; inspect disputed score, comment and evidence; confirm/change with reason; recalculate and retain history. Guide pp. 1–2. | [Review forms](../frontend/src/ReviewForms.tsx), [workflow tests](../tests/test_workflow.py), [browser integrity tests](../frontend/e2e/product-integrity.spec.ts). | Implemented. Accepted review updates the effective result and serious flag; original automatic results remain unchanged. Submission export uses the original automatic assessment. |
| Provide transcript and recording listening or player link. Guide pp. 2, 4. | [Recording view](../frontend/src/Recording.tsx), [recording recovery](../backend/recordings.py). | Supplied safe links are retained; recognized direct audio URLs also have playback controls. External recording availability is outside the application. ASR is not required; diction and intonation are not inferred from text. |
| HTML/CSS/JavaScript, clear launch instructions, future Dynamics adaptation, no required login. Guide pp. 1, 4. | [README](../README.md), [stack boundary](STACK.md), source launchers and clean-source verification. | Implemented web application and backend API boundary. Deployed Dynamics integration has not been tested. Reviewer names are self-entered; there is no authentication requirement for this demonstration. |
| Show section totals if sections are configured. Guide p. 2. | The official checklist has no sections. | Not applicable to the supplied configuration. Section configuration/aggregation is not implemented and would require work if organizers introduce sections. |
| Identify paid model and approximate total cost per evaluation, including extra calls. Guide p. 4. | [Measured performance and costs](PERFORMANCE.md), [README](../README.md). | Actual model and measured costs are disclosed. Repairs and reviews add calls; historical averages are not guaranteed future prices. |

## Checklist fidelity and interpretation limits

The eight criterion kinds, raw answer scales, weights and allowed N/A positions
match the checklist PDF and the results appendix:

| Submission code | Allowed value | Weight |
|---|---|---:|
| `contact` | boolean | 10 |
| `discovery` | boolean or `null` | 15 |
| `identification` | boolean or `null` | 20 |
| `consultation` | 0, 5, 10, 15, 20 or `null` | 20 |
| `empathy` | boolean | 15 |
| `dialogue` | 0, 4, 7, 10 | 15 |
| `closure` | boolean or `null` | 5 |
| `critical` | boolean | Separate flag |

N/A must satisfy its configured applicability condition; missing evidence alone
does not establish N/A. The three-minute first-response threshold, tags and
attachments are excluded as specified on checklist p. 2. The same scales apply
across languages. A serious flag covers the three specified grounds: insult,
off-company paid-service offer, or confidential disclosure. It does not
automatically zero the total.

The operational checklist also contains **team interpretations**, not verbatim
organizer requirements. In particular, the rule assigning consultation level 15
to a wrong prerequisite corrected before customer action is an explicit team
extension; the PDF does not state that special penalty. Detailed action-order,
overlap and uncertain-closing guidance likewise elaborates the shorter source
rules. Terminal thanks may be a farewell depending on context; the PDF does not
settle every such phrase. These boundaries remain subject to review.

The checklist PDF describes chats and has no separate call rubric. Voice-call
adaptation and handling of noisy ASR/post-disconnect fragments come from later
clarification and team implementation, not a call paragraph in that PDF. The
application evaluates the available transcript and preserves material uncertainty.
Any selected product-policy snapshot is an explicit assumption, not proof of the
conversation's date, actual broker or private account state.

## Results format and delivery

The [exporter](../scripts/export_submission.py) and
[JSON 1.0 validator](../cqa/submission.py) implement appendix pp. 1–3:

- Exactly one JSON object at `results/dev/results.json` and
  `results/prod/results.json`, with schema version `1.0`, team name, actual model
  mode/name and one result per original ID. Team name is `polygon`.
- Every successful result contains all eight official codes exactly once, the
  prescribed JSON types, rationale and one-based positions in the **complete
  original transcript**, including client, bot and system turns.
- N/A is `null`, with its weight excluded from the denominator. Scores normalize
  the remaining weighted points to 100 and round to two decimals.
  `critical_flag` equals `critical.value` and remains separate from the total.
- Failure retains the original ID, `status: "error"`, empty `criteria`,
  `score: null` and a reason. It is neither omitted nor replaced with zero.
- Output is UTF-8 JSON. Saved source/checklist/native assessments are validated
  before atomic output replacement. Known DEV data cannot be exported as PROD.

The audited [DEV submission](../results/dev/results.json) contains all **65
original IDs and 520 criterion entries**. All scores were independently
recalculated; 1,577 evidence positions were checked. Revalidating and re-exporting
all 65 selected saved model records reproduced that file exactly. The same DEV
payload was verified on public `main`; 48 focused submission/preflight tests passed.
These checks establish format and provenance, not organizer Ground Truth agreement.

**Remaining delivery:** obtain the real control group when released, process all
ten conversations, export and validate `results/prod/results.json`, and commit
**and push** both required files plus the intended final application changes to
the submitted public repository before stop-code. A local file or local commit
is insufficient. The appendix defines release after 23 hours and stop-code after
24 hours; follow the organizer's actual schedule. Use the
[control release runbook](CONTROL_RELEASE_RUNBOOK.md), preserve every attempt,
and verify the pushed commit and both paths. No DEV subset or prepared example
counts as a control result.
