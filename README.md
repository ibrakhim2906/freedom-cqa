# Freedom CQA

Conversation Quality Analytics prototype for the Freedom Broker hackathon.

Status: project setup and design. The application has not been implemented yet.

## Product goal

Let a quality reviewer configure a checklist, evaluate an operator's conversation,
inspect the evidence behind each judgment, and resolve appeals with a preserved
decision history. Support Russian, Kazakh, and English.

## Agreed design principles

- Evaluate the meaning of the saved criterion against the actual conversation.
- Preserve speaker attribution and original timestamps.
- Produce criterion-specific judgments, explanations, and evidence references.
- Use code for validation and score calculation.
- Keep insufficient evidence distinct from not applicable and from a failed criterion.
- Show unresolved evaluation failures explicitly; do not substitute generic judgments.
- Preserve checklist versions, original evaluations, and human review decisions.
- Verify the final displayed assessment using paraphrases and controlled evidence changes.

## Development environment

Use the Windows-native desktop agent and this Windows checkout initially.
The earlier browser/computer-use limitation with a WSL-hosted project has not
been verified as resolved in this session. WSL is available for targeted commands
if useful. The application stack and model provider remain to be selected.

## Materials and open questions

- The student guide and Freedom introduction have been reviewed.
- Access to the DEV API was verified: 65 conversations were returned.
- The separate official eight-criterion checklist has not been supplied.
- Sample rubrics discussed in chat are illustrative, not official scoring rules.
- Keep dataset records, call recordings, signed API URLs, and credentials outside Git.
- The guide requests a public repository for submission; this repository starts private.

## Progress

See [the progress checklist](docs/PROGRESS.md). Use small commits for reviewable
milestones. There is no application startup command yet.
