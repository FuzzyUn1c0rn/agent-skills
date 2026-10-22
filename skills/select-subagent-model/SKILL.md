---
name: select-subagent-model
description: Choose a model and reasoning effort for delegated work using official OpenAI subagent guidance. Use when preparing to spawn subagents or when asked to allocate models across subtasks.
---

# Select Subagent Model

Choose settings for the actual delegated task. Preserve explicit user model choices, budget preferences, and the scope of authorized delegation. This skill selects settings; it does not require spawning agents.

## Official starting points

Based on the official guidance checked on 2026-10-20:

| Work | Starting model and effort |
| --- | --- |
| Narrow, clear, repeatable tasks and quick scans | GPT-6 Luna; start at high |
| Code exploration, documentation research, small fixes after diagnosis | Official examples use GPT-6 Luna/high |
| Demanding, ambiguous work requiring several steps and sustained context | GPT-6.1 Sol; adjust supported effort to the task |
| Browser investigation | Official example uses GPT-6.1 Sol/medium |
| Problems warranting the strongest reasoning capability | Consider GPT-6 Astra; its explicit-model starting effort is low, then adjust |

The Codex guide recommends Sol for most tasks and Luna for lighter delegated work. Its effort guidance associates low with simple tasks needing speed, medium with balanced depth, high with complex logic and edge cases, and xhigh/max with especially demanding reasoning.

These are starting points and examples, not fixed assignments or repository-specific benchmarks. The broader model-selection guide recommends comparing equivalent inputs and keeping the lightest configuration that meets the required quality.

## Apply the choice

- Consider ambiguity, required context, verifiability, and the consequences of errors alongside cost and latency. A long file inventory can still be a narrow task; a short correctness question can require substantial reasoning.
- Use the models and reasoning levels exposed by the current delegation tool. Current identifiers corresponding to the guidance are `gpt-6-luna`, `gpt-6.1-sol`, and `gpt-6-astra`. Verify availability instead of assuming these identifiers or effort levels are supported everywhere.
- Pass the chosen model and effort explicitly when the tool permits. Respect its context-inheritance restrictions and give the agent the task, constraints, and necessary evidence when a fresh context is required.
- If a requested model is unavailable, disclose that and choose a supported alternative consistent with the user's priorities. Ask only if that substitution would conflict with an explicit requirement.
- Check the returned evidence and results. Incomplete tracing, unresolved contradictions, or failed validation can justify more effort or a stronger model. Avoid escalating solely because a task has a prestigious role name such as "architect" or "reviewer."
- Do not add duplicate evaluation runs to every assignment. Use observed results, and compare alternatives on representative work when repeated usage makes that worthwhile.
- When explaining a selection, distinguish an official recommendation or example from your application of it to this task. Keep the explanation brief.

## Sources and freshness

The [official Codex subagent guide](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning) is the primary source for delegation and effort settings. The [model-selection guide](https://developers.openai.com/api/docs/guides/model-selection) covers broader capability, cost, and quality trade-offs.

Recheck the relevant official pages when asked for current guidance, when available models change, or when the dated guidance conflicts with the runtime. Do not require a new documentation search for every spawn within the same task. If verification is unavailable, identify the guidance as a dated starting point rather than claiming it is current.
