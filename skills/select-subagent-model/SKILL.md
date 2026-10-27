---
name: select-subagent-model
description: Choose a model and reasoning effort for delegated work using official OpenAI guidance and the current tool's capabilities. Use when preparing to spawn subagents or when asked to allocate models across subtasks.
---

# Select Subagent Model

Choose settings for the actual delegated task. Preserve explicit model choices, budget preferences, and authorized scope. This skill selects settings; using it alone does not authorize delegation or changes to saved agent configuration.

## Selection priorities

For this user, prioritize accuracy over speed. Among configurations expected to meet the task's quality bar, minimize total token cost. Account for input, reasoning, output, repeated context, retries, review, and repairs using the actual client's pricing or usage accounting. API token prices do not establish Codex subscription usage. Extra latency alone is not a reason to lower effort. Honor later task-specific preferences or hard budgets.

Choose model and effort together for the work, uncertainty, and consequences of missed errors. A stronger model at moderate effort can be appropriate. Favor enough capability initially to avoid foreseeable rework; keep bounded, easily verified tasks economical.

## Choose a model

Official guidance checked on 2026-10-27:

| Model | Documented fit | Starting effort |
| --- | --- | --- |
| GPT-6 Luna (`gpt-6-luna`) | Clear, repeatable, high-volume work; focused exploration and diagnosed small fixes appear in Codex examples | `high` is the Codex subagent starting recommendation |
| GPT-6.1 Terra (`gpt-6.1-terra`) | Scoped code fixes, visual reasoning, computer use with a defined outcome, concise writing from supplied material | `medium` is the GPT-6 guide's general baseline; adjust to the task below |
| GPT-6.1 Sol (`gpt-6.1-sol`) | Ambiguous work needing planning, tool use, validation, and sustained context; the Codex starting choice for most tasks | Client default; API default is `medium` |
| GPT-6 Astra (`gpt-6-astra`) | The most demanding reasoning, coding, research, and complete workflows | `low` is the Codex explicit-model starting recommendation; adjust for difficulty |

The Codex subagent guide specifically recommends Sol and Luna; Terra's fit comes from the broader model-selection and GPT-6 guides. These baselines and examples do not establish exclusive assignments or comparative performance.

## Match implementation and validation to the task

The following choices apply OpenAI's guidance to this user's priorities. They are practical recommendations, not measured rankings or official task-by-task prescriptions.

| Actual assignment | Model and effort to consider |
| --- | --- |
| Mechanical edits, extraction, or a fixed checklist with readily verified outcomes | Luna; `low` or `medium` can suffice for simple operations; retain `high` when tracing or judgment is needed |
| Focused code mapping, documentation lookup, or repeatable fixes with a clear diagnosis | Luna/`high`; prefer Sol if gathering evidence becomes an ambiguous investigation |
| Scoped code fix or bounded implementation following an established pattern | Terra/`medium` for clear local logic; Terra/`high` when invariants, edge cases, or test design require substantive reasoning |
| Multi-step implementation, uncertain diagnosis, changes across modules or shared state | Sol/`high`; `medium` can suit bounded work with a settled design; `xhigh` for especially difficult interacting constraints |
| Simple UI inspection, a known correction, or a defined screen workflow | Terra/`medium` with explicit criteria and direct verification |
| Subtle visual comparisons, consistency across UI states, interaction edge cases, corrective feedback | Terra/`high`; consider `xhigh` only for unusually demanding comparisons supported by sufficient evidence |
| Code correctness review, meaningful regression-test design, or validation that must challenge assumptions | Sol/`high` when cross-cutting reasoning dominates; Luna/`high` or Terra/`high` can cover a bounded review matching their strengths |
| Exceptionally difficult reasoning, correctness analysis, architecture, or failure modes with costly consequences | Astra; `medium` can suit bounded judgment-heavy work, `high` for complex logic and edge cases, `xhigh` or `max` for the hardest reasoning |

For research and writing, consider Luna for clear extraction, Terra for supplied-material writing or visual work, Sol for sustained synthesis, and Astra for unusually difficult judgment. Role names such as "implementer," "validator," or "architect" do not determine settings.

Terra is a coding candidate for suitable tasks without images. OpenAI specifically recommends scoped fixes; extending that to small implementation tasks is a candidate to verify on representative work. Prefer Sol or Astra when uncertain requirements, dependencies, or consequences exceed that scope. A small diff can require deep reasoning; a large inventory can remain straightforward.

## Calibrate effort

Use only levels supported by the selected model in the current delegation tool. API defaults and supported levels can differ from Codex or ChatGPT clients. Effort labels do not establish equal capability, accuracy, time, or cost across models.

Adjust the model baselines using the task table. Choose higher effort initially when the task needs substantial assumption checking or edge-case reasoning; failing at a lower level is not a prerequisite. Lower effort can fit straightforward, directly checkable work. In particular, Astra's `low` baseline does not prescribe low effort for demanding correctness work. A short prompt alone does not justify lowering effort, and maximum effort on a cheaper model is not an established substitute for a more capable model.

Higher effort can improve quality but does not guarantee it. Reserve `xhigh` or `max` for especially demanding reasoning. Use `none` or `minimal` only when supported and suitable for a simple operation. Use `ultra` only when supported, respecting delegation rules and added usage. Extra reasoning cannot replace missing evidence or tools.

## Use Terra for UI validation

Actively consider Terra for an independent agent that inspects a developing UI, reports evidence to an implementer, and rechecks corrections. Use the task table for model and effort selection. This applies Terra's documented strengths; it is not a benchmark ranking.

Supply the accepted design or reference, acceptance criteria, relevant UI states, and screenshots or application access. Require expected versus observed behavior, location or reproduction steps, and supporting evidence. Distinguish requirement violations from design suggestions. Screenshots establish appearance; interaction claims require exercising the application. Follow project presentation and sampling procedures. Use Sol or Astra when unresolved requirements or difficult reasoning across state and architecture dominate the review.

## Select an adversarial reviewer

Choose settings from the task table for independently testing assumptions, finding counterexamples, and tracing consequences. A cheaper implementer with a stronger reviewer can fit a bounded fix whose verification needs deeper reasoning: for example, Luna or Terra implementing, with Sol reviewing. Include review and repair costs when judging the pairing; savings and accuracy remain unmeasured. Use a sufficiently capable implementer initially.

Supply acceptance criteria and raw artifacts for independent assessment. Require evidence-backed findings, distinguish defects from unresolved concerns, and permit clean reviews. Model diversity alone does not establish independence. This guidance selects settings for authorized review; it does not require extra agents or duplicate review rounds.

## Apply and evaluate

- Check available model identifiers, effort levels, required tools, and context-inheritance rules before spawning. Where supported, pass the chosen model and effort explicitly; account for saved agent settings that may override them. A fresh context needs the task, constraints, necessary evidence, and success criteria. Keep evidence sufficient and reports concise to avoid unnecessary repeated context and output.
- If an explicit model is unavailable, distinguish a preference from a hard requirement. Disclose a supported substitution consistent with a preference; ask before proceeding when substitution would violate a hard requirement. Apply the same rule to effort or budget constraints.
- Verify the result against the task: relevant regression checks for code, rendered behavior for UI changes, saved records for computer use, and facts, qualifications, and audience fit for writing. Follow the project's verification requirements.
- Before escalating after failure, determine whether missing inputs, unavailable tools, or unclear scope caused it. Repair those causes first; use more effort or a stronger suitable model when reasoning or capability is the limitation. A failed check alone does not establish that limitation.
- Define the quality bar before comparing settings. For implementation, assess behavior, regressions, and repairs; for validation, assess missed defects, unsupported findings, and evidence quality. Use observed results rather than duplicate evaluation runs for every assignment. For representative comparisons, hold inputs, tools, criteria, and effort constant while comparing models; then vary effort. Reduce cost only while preserving the required accuracy. Explain selections briefly and distinguish source guidance from task-specific judgment.

## Sources and freshness

- [Codex subagent guide](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning): delegation, model starting points, effort, and examples.
- [Model-selection guide](https://developers.openai.com/api/docs/guides/model-selection): Terra's scoped coding role and quality, cost, and latency comparisons.
- [GPT-6 guide](https://developers.openai.com/api/docs/guides/latest-model): family capabilities and Terra's medium starting effort.
- [Reasoning guide](https://developers.openai.com/api/docs/guides/reasoning): model-dependent settings and reasoning-token trade-offs.
- API model pages for [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra), [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), and [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra): identifiers, API settings, and specifications.

Recheck relevant official pages when asked for current guidance, available models change, or dated guidance conflicts with the runtime. Reuse verified guidance within the same task. If current verification is unavailable, disclose the dated basis and follow the current tool's actual capabilities.
