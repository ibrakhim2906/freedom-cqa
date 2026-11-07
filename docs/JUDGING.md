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
- The actual eight-criterion operator checklist remains a separate required input.

The earlier 100-point judging rubric discussed in chat was hypothetical. It is
not the organizer's rubric and must not be represented as official weights.

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
