# DEV data audit

Reviewed on 2026-11-07 against the organizer DEV response and all three supplied PDFs.
All 65 transcripts were inspected. Audio recordings were not listened to.
No model evaluation calls were made and no accuracy claims are made here.

Raw source: local, Git-ignored `data/private/dev.json`. Never commit that file or
the signed organizer endpoint. SHA256 of the locally serialized JSON snapshot:
`98d70ed5e21b7502bec01fd87daee43b6beb670791dfe63bfb469c3919dc29dd`.

## Corpus facts

| Property | Observed value |
| --- | --- |
| Conversations / unique IDs | 65 / 65 |
| Synthetic chats | 60: 30 RU, 15 KZ, 15 EN |
| Real calls | 5, all RU |
| Transcript messages | 1,268: 882 in chats, 386 in calls |
| Speaker roles | client, bot, system, operator |
| Transcript text lengths | 769 minimum, 990 median, 5,089 maximum characters per conversation |
| Ground Truth / evaluation fields | None in the supplied response |
| Chat timestamps | MM:SS |
| Call timestamps | ISO 8601, with timezone and fractional seconds |
| Audio links | Present for all five calls |

The text totals 84,054 characters across the corpus. Individual transcripts are
small enough to evaluate with their full context; transcript retrieval/chunking
would introduce unnecessary opportunities to miss a late question or system event.

## Findings that affect the evaluator

1. **Bot context precedes every synthetic operator interaction.** Bot greetings,
   consent notices, handoff messages, and clarifying questions recur. Their facts
   are context; their actions must not automatically be credited to the operator.
2. **Several scenarios recur across languages.** Tariff lookup, funding details,
   profile updates, statements, login reuse, securities lookup, margin settings,
   and identity bypass have close relatives. Randomly splitting rows can place
   related/translated scenarios on opposite sides of an evaluation split.
3. **Late questions materially change completeness.** Four synthetic chats contain
   24 or more messages. Examples include a missing portfolio position followed by
   a report request, and a transfer inquiry followed by report-download questions.
   A customer saying thanks is not necessarily the final request boundary.
4. **A correct final answer can follow an earlier poor interaction.** Examples
   contain redundant questions, irrelevant advice, later corrections, or requests
   to repeat previously supplied information. Consultation and communication
   quality must remain separate judgments.
5. **Identity and confidentiality require temporal evidence.** Four synthetic
   chats explicitly confirm identity in system messages. Other synthetic cases
   disclose an account restriction while the customer challenges the lack of
   verification. These observations are not official labels for the whole corpus.
6. **End-of-conversation events matter.** Four synthetic cases explicitly contain
   customer disconnection/departure. Some others are closed by the operator. These
   events have different implications for closing applicability.
7. **Calls contain substantial transcription noise.** Technical terms, names,
   sentence boundaries, and some statements are malformed. Preserve original
   evidence and avoid treating every transcription artifact as poor spoken grammar.
8. **One call contains an internal consultation while the customer is on hold.**
   The same `operator` role labels both customer-facing speech and internal speech.
   Hold/consultation system events provide boundaries. Internal speech must not
   automatically count as an explanation, farewell, or disclosure to the customer.
9. **Redactions are not evidence that an action was omitted.** A hidden name may
   still occur in an explicit self-introduction. Hidden verification data must be
   interpreted with surrounding confirmation and sequence evidence.
10. **Customer-provided information and operator disclosure are different events.**
    Quoted misconduct, ordinary verification exchanges, internal consultation,
    and disclosure to the customer must be distinguished under the actual rubric.

## Concrete review cases

These are audit observations, not organizer Ground Truth annotations.

| Case(s) | What they exercise |
| --- | --- |
| p1-ru-003 | Two substantial questions; a tariff-location answer does not resolve the commission question. |
| p1-ru-007, p1-en-007 | Profile-update navigation answered; when withdrawal can be retried remains unanswered. |
| p1-ru-014, p1-kz-008 | Information supplied before handoff is asked again; introduction/closing issues also need separate assessment. |
| p1-ru-009, p1-kz-015, p1-en-014 | Individual account restriction disclosed without confirmed identity. |
| p1-ru-010, p1-ru-027, p1-kz-003, p1-en-006 | Multiple requests and follow-ups across longer dialogues. |
| p1-ru-012, p1-ru-025, p1-kz-011, p1-en-009 | Explicit disconnection/departure and criterion-specific N/A conditions. |
| p1-ru-022, p1-ru-023, p1-kz-013, p1-en-013 | Offers of private paid services; customer refusal does not remove the flag. |
| p1-ru-029 | Customer-facing rudeness despite a later useful answer. |
| p1-ru-028 | Warning before a wait, followed by a specific answer. No invented three-minute penalty. |
| p4-ru-002 | Internal consultation, hold boundaries, multiple speakers sharing the operator role. |
| p4-ru-004 | Noisy verification sequence, customer inconvenience, and a follow-up after the end event. |

## Audio access observation

HEAD requests returned HTTP 200 but no useful audio type/length. Small ranged GET
requests to all five exact supplied URLs returned `text/html`, not a recognizable
audio header. This does not prove the recordings are inaccessible: the URLs may
be browser preview/share pages. Resolve the authorized playback route before
using them as an audio element source or sending recordings to an audio model.
No raw recordings were downloaded or assessed.

Call timestamp spans include IVR, recording state changes, and hold intervals.
Do not assume subtracting the first transcript timestamp gives an exact seek
offset into the recording without checking alignment.

## Evaluation consequences

- Group near-duplicate/translation families when reserving evaluation cases.
- All supplied transcripts have now been inspected for design. Do not describe
  this corpus as an entirely unseen test set.
- Reserve labels and cases from subsequent prompt tuning and add fresh cases
  with reference decisions frozen before seeing evaluator output.
- Keep AI-proposed labels distinct from human-reviewed reference labels and
  from actual organizer Ground Truth.
- Test both invariance under paraphrase and appropriate changes under evidence,
  speaker, sequence, disconnection, and rubric changes.
- Report per-criterion, language, and channel behavior separately. The supplied
  corpus contains no KZ/EN real calls, so it cannot establish performance on them.
