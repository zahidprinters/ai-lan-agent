---
description: "Create a reusable .prompt.md from a repeatable workflow in the current conversation. Use when a user repeatedly asks for the same task style and wants a slash-command prompt."
name: "Create Prompt From Workflow"
argument-hint: "Describe the workflow to templatize, expected inputs, and output style."
agent: "agent"
---
Build a high-quality .prompt.md that turns a repeatable workflow into a reusable slash command.

Process:
1. Review the active conversation and extract:
- the repeated core task
- implicit inputs (selection, file type, repo context, constraints)
- desired output format, tone, and success criteria
2. If repetition is unclear, ask concise clarifying questions:
- what task should the prompt automate
- whether to use arguments or fixed context
- workspace scope or user-profile scope
3. Draft the prompt file with valid frontmatter and focused body instructions.
4. Save the file to one location:
- workspace: .github/prompts/<name>.prompt.md
- user profile: {{VSCODE_USER_PROMPTS_FOLDER}}/<name>.prompt.md
5. Identify weak or ambiguous areas and ask for only the minimum decisions needed.
6. Finalize by summarizing:
- what the prompt does
- example invocations
- 1 to 2 related prompts the user may want next

Quality bar:
- Keep one prompt focused on one task.
- Use concrete, actionable instructions.
- Include output structure when format consistency matters.
- Avoid multi-task prompts and vague descriptions.
- Keep repo-specific links minimal and relevant.

Output format:
- Prompt file path
- Final prompt content
- Two example invocations
- Follow-up options