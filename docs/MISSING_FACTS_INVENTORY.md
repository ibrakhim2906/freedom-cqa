# Missing facts inventory — 2026-11-07

This is a source/evidence inventory, not a knowledge base, expected-score file or new benchmark. It is never loaded by the runtime evaluator. No model inference was run and no score, label, checklist or evaluator behavior was changed.

Subsequent official-source research is recorded in [OFFICIAL_PRODUCT_FACTS.md](OFFICIAL_PRODUCT_FACTS.md), with [five complete conditional reviews](COMPLETE_ASSESSMENT_REVIEW.md). The inventory below remains the original audit snapshot; later findings do not rewrite its source records or the original evaluations.

All 65 supplied source transcripts (1,268 messages) were reviewed, together with the four organizer PDFs, organizer clarifications recorded in the project, and the three previously collected platform guides. Call recording links were registered; recordings were not listened to.

## What the materials establish

| Material | What it supplies | What it does not establish |
| --- | --- | --- |
| Data 2 (1) 1.pdf, five pages | Brand/ecosystem background; page4 states FRHC trades on Nasdaq | Account rules, current tariffs, withdrawal timing, KYC procedures, or Nasdaq-versus-NYSE sector comparison |
| Student Guide v3, four pages | Configurable checklists, full evaluation/review workflow, DEV structure, call recordings, changed-criterion control and delivery process | Per-conversation correct answers or operational product handbook |
| Chat Quality Checklist, three pages | Exact criteria, scales, weights, N/A, verification ordering, separate critical flag and source-evidence expectations | Every broker-specific product/procedure fact |
| Results Appendix, three pages | Exact JSON1.0 fields, original IDs/turn numbering, nullable N/A values and explicit error records | Expert labels, a partial/review record status or a hidden numerical selection formula |
| Organizer clarifications supplied in chat | Call adaptation, reasonable uncertainty, flexible checklists and emphasis on justified working results | Public score weights or a requirement for universal documentary proof of every ordinary claim |
| common_messages.json and DEV bot replies | Conversation context and recurring messages | Independent authoritative product policy |
| Existing three-guide reference pack | Scoped support-contact, password-recovery and profile-update excerpts | All entities, historical validity, fees, private account facts, desk routing or all product topics |

The existing guide excerpts were gathered independently during development, not supplied as an organizer product-policy handbook. The organizer says product/service materials exist, but the four attached PDFs are not a complete operating manual. This audit does not claim no such documentation exists elsewhere.

## Highest-value unresolved product facts

Five reusable topic groups concern 13 distinct chats: withdrawal after profile updates (RU008/KZ004), login reuse after closure (RU015/KZ007/EN001), D-account eligibility (RU024/KZ011/EN010), form1042-S language options (RU012/KZ014/EN011), and margin effects on existing holdings (RU020/EN008). These are candidates for focused authoritative documentation, not 13 promised finalized results. Some also have closing uncertainty or unanswered requests.

For each source, establish entity/platform applicability and any actual document/effective date. Keep retrieval date distinct from policy validity. Do not infer jurisdiction from conversation language, copy bot answers into policy, or attach one platform guide to all entities.

## Reusable topic inventory

Case counts below are source associations, overlap between topics, and include resolved/observed behavior. They are not counts of wrong scores or claims that a lookup is required. The private index gives every original message pointer.

| ID | Topic | Cases | Available evidence | Priority |
| --- | --- | ---: | --- | --- |
| F01 | Tariff location and temporal meaning | 7 | local outcomes only | high |
| F02 | Trading and funding commissions | 2 | not supplied | medium |
| F03 | Bank-transfer details and currencies | 5 | local outcomes only | low |
| F04 | Broker report generation | 7 | local outcomes only | low |
| F05 | Personal-data update route | 5 | scoped external reference exists | high |
| F06 | Withdrawal after profile update | 5 | not supplied | high |
| F07 | Private account/order facts | 6 | private records absent | high |
| F08 | Verification prerequisite for protected disclosure | 10 | official rule supplied | high |
| F09 | Information-site versus trading access | 6 | local outcomes only | high |
| F10 | Login reuse after closure | 3 | not supplied | high |
| F11 | Security search and order navigation | 7 | local outcomes only | medium |
| F12 | Margin control location | 4 | local outcomes only | medium |
| F13 | Margin effect on existing holdings | 2 | not supplied | high |
| F14 | D-account versus trading account | 3 | not supplied | high |
| F15 | Form1042-S language availability | 3 | not supplied | high |
| F16 | Company financial-statements navigation | 2 | local outcomes only | medium |
| F17 | Nasdaq versus NYSE explanation | 1 | related background only | medium |
| F18 | Support and personal-manager service scope | 1 | not supplied | high |
| F19 | Security-specific exchange/OTC availability | 3 | not supplied | high |
| F20 | Trader/support contact and hours | 2 | not supplied | high |
| F21 | Internal OTC commission claim | 1 | not supplied | low |
| F22 | Demo-account reset | 1 | not supplied | high |
| F23 | Citizenship/residence document selection | 1 | not supplied | high |
| F24 | Investigation and follow-up commitments | 10 | commitment observable | medium |

## Avoid unnecessary verification work

- **Verification prerequisite:** checklist pages1 and3 already require confirmation before established protected disclosure/action. Do not demand another product manual to apply that grading rule. Actual account truth remains a different question.
- **Missing answers:** fee and withdrawal-timing omissions can be established without knowing the correct fee/timing. A policy source becomes necessary only where its truth can change the allowed grade.
- **Observed task success:** a successful report download or login supports the particular observed outcome. It does not certify every optional route, permanent eligibility or unrelated account state.
- **Appropriate next steps:** the rubric permits a concrete next step. Distinguish an observable investigation commitment from proof that the backend action or eventual investigation succeeded; do not require completion evidence when the criterion does not.
- **Internal speech:** the OTC fee statement is an internal consultation claim. Missing tariff evidence does not automatically create a customer-facing error or a duty to recite the fee.
- **Noisy calls:** missing reliable speech/end-state evidence may require audio or manual review. Product documentation cannot resolve whether a garbled phrase was spoken clearly or whether the operator could say goodbye.

## Recoverable metadata versus genuinely missing information

All five call transcripts explicitly date the source events to 2026-11-03, but their frozen Conversation.occurred_on is null. That is a recoverable input-metadata gap. Preserve the original timestamp/timezone and derivation provenance when implementing a future fix; do not rewrite frozen inputs.

Chats provide MM:SS only; their actual dates and exact knowledge scopes remain absent. The cached references' same-day window (2026-11-07 only) and exact scope gate were conservative team design choices, not organizer requirements or documented legal effective dates. Correcting the call date would not make a Nov7-only guide applicable to Nov3. Neither silently dropping applicability checks nor inventing a policy window is justified.

## Files and reproducibility

- `audits/fact-requirements-v1.json`: 24 reusable questions, required evidence and limitations; no proposed scores.
- `audits/organizer-fact-spans-v1.json`: source pointers to statements/questions; not inference input.
- `artifacts/facts-audit-v1/inventory-and-audit.json`: private joined index of all65 source/result pairs, fact occurrences, findings, metadata and hashes.
- `artifacts/facts-audit-v1/materials/manifest.json`: exact PDF paths/hashes/pages; extracted text is private.
- `artifacts/facts-audit-v1/materials-review.json`: 20 official rules with document/page pointers and team-policy distinctions.

Run `uv run python -m scripts.build_existing_results_audit` to validate source pointers, revalidate all saved assessments/arithmetic, and rebuild the offline report. It has no model client or network path. The ledger was unchanged: 548 rows, latest call548, settled sum $19.694328. Audit incremental API cost: **$0**.
