# Saved checklists

`freedom-reviewed-016.json` is the default configuration. It retains the supplied
criterion weights and permitted answer levels, with explicit team interpretations
for ambiguities such as task clarification, overlapping deductions and corrected
advice. These interpretations are configuration, not hardcoded scoring rules.

In particular, a wrong prerequisite corrected before customer action, followed by
resolution without established remaining consequences, receives consultation15/20.
An independent unresolved request, wrong remaining advice or harm can justify a
lower configured level.

`freedom-reviewed-015.json` remains available because43 preserved DEV results were
generated with that version. Older immutable versions support historical records.
They are not selected as the default on a fresh checkout.

Use the UI to save a new version when changing criteria, descriptions, answer types,
weights, N/A conditions or scales. The assessor uses that exact saved configuration;
it does not look up expected answers by conversation ID. Version/content conflicts
are rejected instead of silently rewriting an existing checklist.
