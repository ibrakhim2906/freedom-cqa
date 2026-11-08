# Delivery plan — 8 November, 11:50 UTC+05:00

Target: an impressive, dependable conversation-quality product that can credibly
compete at the 95–100 quality level. That target is not an official organizer score
or a prediction. Ship substantive improvements; use a small number of decisive
checks after coherent changes, not repeated large test runs.

## The product we are building

A reviewer imports a new conversation, chooses or changes a checklist, receives
clear criterion decisions, follows each decision to original evidence, challenges
a decision, and exports the preserved original and reviewed results. The experience
must work on RU/KZ/EN chats and supplied call transcripts. No prepared-score lookup.

The key core change is a compact rubric-first assessor. It evaluates the actual
criterion against the complete conversation, records decisive evidence and material
uncertainty, and uses code for quotations and arithmetic. A focused independent
review challenges consequential decisions. It does not require a global proof graph
or an inventory of every possible factual claim before delivering a judgment.

## Parallel ownership

| Workstream | Owner | Concrete deliverable |
|---|---|---|
| Assessor | Core agent | Compact schema, full-source prompt, exact evidence resolution, supported decisions and localized uncertainty |
| Product interface | UI agent | Professional review workspace, searchable/filterable queue, clear outcomes, evidence navigation, usable appeals and checklist editing |
| Decision cases | Evaluation agent | Six difficult source-grounded cases plus a changed-criterion pair; expectations kept outside model inputs |
| Integration and delivery | Root | API orchestration, focused reviewer, persistence, scoring, exports, spending cap, final walkthrough and delivery |

Work happens in `freedom-cqa-delivery`, branch `codex/impressive-cqa-delivery`.
The original chat can finish its isolated lean-v2 experiment without conflicting
with this worktree. Preserve earlier results and the existing source checkout.

## Core implementation

1. One full-source assessment produces each configured criterion's allowed answer,
   concise rationale, decisive source IDs, counterevidence, omission interval when
   relevant, deduction reason, and material missing information.
2. Code resolves source selections, validates roles/chronology/allowed outcomes,
   calculates N/A normalization and flags, and saves the exact runtime identity.
3. Factual assurance is criterion-specific. A proposed investigation is evaluated
   as a next step; it is not required to prove future backend completion. An
   unanswered question can be established without knowing the missing answer.
4. Unknown facts do not become verified facts. When a genuinely material unknown
   prevents a defensible decision, that criterion stays reviewable. No guessed
   date, broker identity, hidden completion, or automatic N/A substitution.
5. A focused independent pass checks configured flags, high-impact decisions,
   unresolved criteria and difficult boundary judgments against the full source.
   Disagreements and failed review calls remain visible. Never average arbitrary
   grades or silently pick a more favorable retry.
6. Reuse the provider, accounting, scorer, application and appeal infrastructure.
   New records have a distinct assessor version; old audits retain their meaning.

## Product changes

- A useful conversation queue with search, language/channel filters and visible
  selection. Counts are calculated from real records.
- Clear transcript and assessment workspace; source clicks highlight actual text.
- Scannable criterion outcomes, weights/contributions, deduction reasons and
  material uncertainties. Detailed provenance remains available without dominating.
- Human review preserves the AI result and shows the reviewed outcome and reason.
- Saved results reopen without inference. Failures have specific recovery actions.
- New criteria are saved and evaluated through the same configurable engine.
- Call recording links remain accessible; playback only where the supplied link
  is actually playable. Never claim audio analysis from a transcript.
- Useful empty/loading/error states, keyboard-accessible controls and responsive
  layout. No invented analytics or fake results for visual polish.

## Time cutoffs (local time)

| Cutoff | Outcome |
|---|---|
| 06:30 | New assessor, API integration and substantial UI changes assembled |
| 07:30 | One focused real-provider run and full-result inspection; fix observed blockers |
| 08:00 | Commit to one core architecture; stop opening new architectural alternatives |
| 09:30 | Complete real import → assess → evidence → appeal → revised result → export |
| 10:30 | DEV processing, export validation, README and five-minute demonstration ready |
| 11:00 | Feature freeze; process control inputs when organizers actually release them |
| 11:35 | Final delivery candidate and source/result completeness check |
| 11:50 | Delivery deadline with known limitations clearly recorded |

Move remaining optional work out when a cutoff is missed; preserve time for the
actual runnable product. Do not spend the final hour on a speculative redesign.

## Verification budget

Build complete feature slices first. Run the frontend build and focused core checks
once after integration, then only rerun checks related to an observed failure.
No repeated 755-test runs after cosmetic or one-line changes. The high-value live
checks are: real new input, both sides of a serious-error contrast, a true omission,
a legitimate next step, multilingual source evidence, and a changed criterion.
Inspect complete outputs, not just whether JSON passes validation.

Success indicators: high completion on determinate cases, preserved real deductions,
no invented evidence, sensible handling of known uncertainty, stable important
decisions, and a working complete review journey. Six examples are a release check,
not a statistical certificate of 95–100 accuracy.

## Spending and final artifacts

User subsequently specified **$5 available now** and requested notice before more
is needed. This replaces the earlier proposed $15 budget. Preserve previous usage,
track every new attempt, and stop before exceeding $5 additional spending.
Use small initial probes before the full DEV run. Provider balance is separate
from the local cap; a top-up may still be needed.

Deliver: runnable app; new versioned assessor and actual measured results; valid
DEV export and control export only if supplied; reproducible README; preserved
appeal history; five-minute demo sequence; final commit with no secrets/private
transcripts accidentally published. Repository publication requires the user's
existing authorization or an explicit final authorization if not already given.

## Five-minute demonstration

1. Import a fresh conversation and show checklist selection and real progress.
2. Explain a useful finding using exact evidence; show justified N/A and the score.
3. Challenge one criterion, record a reviewer decision and show recalculation.
4. Change a criterion and show the new version genuinely changes evaluation.
5. Show saved history/export and the measured limitations in one concise view.


## Later user decisions, implemented before delivery

- User requires numerical judgments for every assessed conversation. V3 makes
  the most defensible configured decision while retaining precise uncertainty;
  the user rejected whole-score abstention for missing policy facts.
- User delegated the policy-context choice. The 22 previously unscored DEV inputs
  use the explicit assumed Freedom Finance Global platform snapshot as of
  2026-11-07, without changing actual source dates, scope or message content.
- User selected consultation 15/20 for a wrong prerequisite corrected before
  customer action, followed by resolution without established remaining harm.
  This is saved as reviewed016; historical rules and labels remain intact.
- User explicitly authorized a further $2 and confirmed available credit. Total
  additional authorization is now $7. This replaces the earlier $5-only cap.
- Independent review now checks every configured criterion, including confident
  full-credit decisions and material changes in certainty. Custom flag display
  and reviewer-selected appeal evidence were corrected.
