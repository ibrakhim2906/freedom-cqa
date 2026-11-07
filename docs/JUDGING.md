# Organizer selection criteria

Source: organizer announcement supplied by the user in chat on 2026-11-07.
This records the announcement; no numeric weights or comparison formula were supplied.

## Selection process

The principal criterion for top-50 selection is accuracy of AI conversation
evaluation. During the control stage, teams receive 10 previously unseen
transcripts. System-assigned evaluations will be compared with prepared Ground
Truth evaluations; closer results are better.

Additional considerations:

1. Functionality and distinctive useful features, technical solutions, and implementation quality.
2. Usability of the interface and the complete evaluation workflow.
3. Process correctness: genuinely analyze new conversations and apply the configured criteria rather than reproduce prepared results.
4. Diversity of technical approaches, including representation of local LLM and cloud AI architectures.

Final selection considers these factors together and is not an automatic ranking
by a single numeric measure. The announcement does not specify architecture
quotas or a scoring advantage for either local or cloud models.

## Implications for development

- Prioritize criterion-level agreement with human-reviewed labels and check the final aggregate score.
- Preserve fresh development cases for checking generalization after prompt changes.
- Analyze errors across Russian, Kazakh, and English and across N/A, omissions, and ambiguous cases.
- Check meaningful input and checklist changes alter the appropriate judgments.
- Preserve evaluation provenance so live analysis and saved results can be distinguished.
- Develop useful evidence and appeal workflows while keeping evaluation accuracy the main priority.
- The actual eight-criterion operator checklist has now been supplied and reviewed.

The earlier 100-point judging rubric discussed in chat was hypothetical. It is
not the organizer's rubric and must not be represented as official weights.

## Later clarification and submission appendix

The organizer reiterates that there is no fixed public formula or ranking. Expert
proximity, an internal repository check, functionality/usability, useful product
features, and diversity of technical approaches jointly inform selection. Build a
working corporate review product; do not optimize against an invented selection
formula. Audience: managers, directors, QA specialists and ordinary employees.
Professional, clear workflows and visual style matter; a cartoon/game theme is
not appropriate for the stated corporate customer.

The new three-page appendix defines mandatory JSON 1.0 result files, exact
criterion codes/types, full-transcript evidence positions and explicit errors.
It supplies no expert-labelled conversations. See [submission format](SUBMISSION_FORMAT.md).

## Further organizer clarification supplied in chat, 2026-11-07

Exact point-for-point agreement is not expected, and expert evaluations can differ.
The organizers emphasize a working system that meaningfully analyzes new dialogue,
applies the selected checklist, and produces logical, justified, reproducible
assessments. Ground Truth comparison considers closeness and overall adequacy.

N/A, serious errors, incomplete data and disputed claims must be handled reasonably;
the system must not invent facts to fill missing information. Calls should account
for spoken communication, without requiring perfect transcription of every word
or pause. Interface usability, the complete process, useful additional capabilities
and the technical approach also matter. The organizers explicitly discourage
spending excessive time guessing their internal grading methodology.

Development consequence: close the focused core-validation phase after the
documented grounding/boundary checks; retain genuine uncertainty and measured
limitations. Complete and verify the real evaluation/evidence/review workflow.
This clarification does not provide a numeric selection formula or guarantee a score.

## Original announcement

**Критерии отбора топ-50 команд**

Основным критерием будет **точность AI-оценки диалогов**.

На контрольном этапе команды получат дополнительный набор из 10 ранее неизвестных
транскриптов. Мы сравним выставленные системой оценки с заранее подготовленными
эталонными оценками (Ground Truth). Чем ближе результаты к эталону, тем лучше.

Помимо точности, будем учитывать:

1. **Функциональность и уникальные возможности:** дополнительные полезные функции, интересные технические решения и качество реализации.
2. **Удобство использования:** насколько понятен интерфейс и насколько удобно организован весь процесс оценки диалогов.
3. **Корректность процесса:** действительно ли система анализирует новые диалоги и применяет заданные критерии, а не воспроизводит заранее подготовленные результаты.
4. **Разнообразие технических подходов:** при формировании топ-50 постараемся сохранить представительство разных архитектур, в частности решений на локальных LLM и облачных AI-сервисах.

**Важно:** точность относительно Ground Truth будет главным ориентиром, но итоговый
отбор не сводится к автоматическому рейтингу по одному числовому показателю.
Решение будет приниматься с учётом совокупности перечисленных факторов.
