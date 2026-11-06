---
name: appsec-engineering-severity-request
description: Create short, recipient-specific engineering messages that collect missing facts for an AppSec severity assessment.
---

# AppSec engineering severity request

Create short messages that AppSec can send through Slack or another chat tool. The goal is to get the missing facts needed to continue a severity assessment.

Analyse the evidence before writing, but keep that analysis out of the engineering message. The message is an information request, not the assessment itself.

This skill does not authorize new security testing, access to secrets or customer data, Jira changes, or sending messages.

## Inputs

Use the material the user supplies:

- Jira ticket key or URL.
- Investigation evidence or an existing AppSec assessment.
- Recipient names, teams, or areas of responsibility.
- Corrections about what was and was not demonstrated.
- Requested output path or message format.

When Jira access is available, retrieve the complete issue, including custom fields and comments. Treat Jira and the supplied investigation evidence as factual sources. Do not present an untested impact as confirmed.

Use the actual Jira URL. Ask for it if it cannot be established. Never invent a Jira site URL.

## Select the questions

Identify the facts that AppSec still needs to decide severity. Rank them by how much the answer could change the assessment.

Select no more than five questions for the whole first round. Prefer fewer questions when they are enough.

Choose questions that:

- Ask for one fact or closely related set of facts.
- Can change the severity assessment.
- Can be answered from product, data, cloud, permission, deployment, or log information.
- Refer to the exact affected resource.
- Do not repeat confirmed evidence.
- Do not depend on an answer that has not been received yet.

Defer lower-priority and dependent questions to a later round. The first message should start a conversation, not complete the whole investigation.

When a broad term may be unclear, add brief examples inside or directly after the question. Examples explain what the answer should cover. They are not confirmed findings or a complete checklist.

## Route the questions

Route each question to the person or team most likely to know the answer.

Use supplied recipient names when available. Otherwise, label the intended role, such as:

- Service owner.
- Data owner.
- AWS or cloud-platform owner.
- Kubernetes platform owner.
- Identity and access management owner.

Never invent a person's name.

Ask each recipient no more than three questions. If one person appears to own more than three, send the three most important questions now and defer the rest.

If several teams own different answers, create a separate self-contained message for each team. Across all first-round messages, never exceed five questions.

Do not send the same question to several recipients unless ownership is genuinely unclear. In that case, ask who owns the answer rather than requesting duplicate work.

## Message content

Each message contains only:

1. The Jira ticket link.
2. A brief reason for the request.
3. A short finding summary.
4. The questions for that recipient.

State clearly that AppSec is carrying out an impact and risk assessment of the vulnerability and needs the information to determine the appropriate severity. Do not ask engineering to choose the severity.

The first sentence of the summary names the vulnerability type in plain language. Keep the summary to two or three short sentences. State the affected product, service, vulnerable field, and confirmed behavior needed to understand the questions.

Include exact resource identifiers where they help the recipient recognize the asset:

- HTTP method and full endpoint URL.
- Full S3 bucket or object URI.
- Cloud account, region, resource name, and resource ID when known.
- Kubernetes environment, namespace, workload, and full service-account subject when known.
- Database, schema, table, tenant, field, resolver, or product component when known.

Do not guess missing identifiers. Remove credentials, signed query strings, cookies, tokens, passwords, and secret values.

Keep each message under about 300 words. Use short sentences and common English. Keep exact technical names unchanged.

An optional final sentence may ask the recipient to point AppSec to the correct owner when responsibility is uncertain.

## Keep internal analysis out

Do not include these items in the engineering message:

- Bugcrowd VRT analysis.
- A proposed or minimum severity.
- A severity floor.
- P1 through P5 decision factors.
- A full evidence inventory.
- A list of every non-finding.
- General environmental commentary.
- Remediation or delivery questions.
- Instructions asking engineering to choose the severity.
- Investigator provenance or detailed internal assessment reasoning.

Use those details to select good questions, not as content for the recipient.

If the user explicitly requests an internal AppSec working note, save it separately from the engineering messages. Never combine the working note and the Slack-ready request in one document.

## Output format

Use this structure:

```markdown
# <ticket>: engineering questions

## Message for <recipient name or role>

Hi <name or team>, I need your help with [<ticket>](<actual-ticket-url>).

I am carrying out an impact and risk assessment of this vulnerability. I need this information to determine the appropriate severity.

<Two or three sentence finding summary. Name the vulnerability type first and include the exact affected resources needed for these questions.>

Could you confirm:

1. <Question for this recipient, with brief examples if useful.>
2. <Optional second question.>
3. <Optional third question.>

<Optional ownership-routing sentence.>
```

Add another `Message for` section only when a different recipient owns other first-round questions.

## Saving the result

Use the output path supplied by the user.

Otherwise:

- If a directory named after the Jira key exists, save as `<JIRA-KEY>/engineering-severity-context-request.md`.
- Otherwise save as `<jira-key-lowercase>-engineering-severity-context-request.md` in the current directory.
- Without a Jira key, use `<finding-slug>-engineering-severity-context-request.md`.

When revising an existing request, preserve confirmed facts and explicit user corrections unless newer evidence replaces them.

Completion means the output contains the actual Jira link, briefly explains that AppSec needs the answers for an impact and risk assessment, names the vulnerability type, identifies the exact affected resources needed by each recipient, asks no more than five questions in total and no more than three per message, routes every question to a likely owner, uses brief examples where needed, contains no internal severity analysis, and is ready to paste into chat.
