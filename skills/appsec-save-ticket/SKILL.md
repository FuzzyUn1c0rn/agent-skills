---
name: appsec-save-ticket
description: Save verbatim Markdown transcriptions of a Jira issue and its direct duplicates in one AppSec folder.
disable-model-invocation: true
---

# AppSec save ticket

Use this skill only when the user explicitly invokes `$appsec-save-ticket`. Save the named AppSec Jira issue and any issues directly linked as its duplicates as faithful, human-readable Markdown copies of their current fields for offline work. Each archive is a transcription, not a summary or assessment. Do not validate the finding, change Jira, or share anything externally.

## Input and destination

Accept a Jira key or Jira URL. Resolve the canonical key from the retrieved issue.

Use the current workspace's `<JIRA-KEY>/` folder for the named issue and all its duplicate exports. If it does not exist, create it. Keep every triage artifact for that ticket in this same folder; do not place ticket-specific files at the workspace root.

Save the named issue as `<JIRA-KEY>/ticket-<JIRA-KEY>.md` and each duplicate as `<JIRA-KEY>/duplicate-<DUPLICATE-JIRA-KEY>.md`. Use the full canonical Jira key in each filename, for example `ticket-VM-1712.md` and `duplicate-VM-1713.md`. Replace earlier exports for the same issues; leave unrelated files untouched. If the folder contains the named issue's old `jira-ticket.md`, remove it after verifying its replacement.

## Retrieval

Use the Atlassian Rovo connector. Resolve the accessible Atlassian resource once, then retrieve the named issue with the `full` view, rich-text in HTML, and rendered fields. Inspect its issue links and collect every distinct issue directly connected by a `Duplicate` link, in either direction (`is duplicated by` or `duplicates`). Include these linked issues regardless of their Jira workflow status; status alone does not establish a duplicate link. Retrieve each linked duplicate with the same view and field options. Do not follow links from those duplicate issues.

Use each retrieved issue's current fields only; omit the activity stream, native comments, and change history even if a full issue response embeds them. If a linked duplicate cannot be retrieved or saved, report its key and the failure to the user; do not silently omit it or invent its contents.

For each retrieved issue, render its current fields, rich text, and attachment and issue-link metadata as simple Markdown. Record its retrieval date and attachment count. Download attachment files only when the user separately asks for them. Use each field's source body for the transcription; use rendered fields to resolve formatting, not to replace source words or duplicate content.

Use the Jira ticket as evidence only. Do not perform triage, security testing, status changes, comments, assignments, external sharing, or outbound messages as part of this skill.

## Archive format

Each archive is an offline copy of its own current Jira issue, not a Jira transport dump. Apply the same format to the named issue and every duplicate. Use only standard Markdown: headings, paragraphs, links, emphasis, lists, tables, and fenced code blocks for technical evidence.

Start with a `## Ticket overview` table. Include every non-empty issue-level metadata field, including standard fields, custom fields, source context, vulnerability classification, priority, status, people, dates, labels, links, endpoint, and attachment count. Put long rich-text field values in named sections and link to them from the table. Render compound metadata legibly without dropping constituent values.

Transcribe each rich-text field in its original paragraph, heading, list, table, and evidence order. Preserve the author's exact words, spelling, capitalization, punctuation, numbers, identifiers, and repetitions. Convert formatting syntax only; do not paraphrase, compress, correct grammar, insert narrator language such as “the ticket reports,” or reorganize the author's content. Section headings added to identify Jira fields are allowed. Render these sections as applicable:

- `## Description`
- `## Remediation`
- `## Attachments` (metadata only)
- `## Linked issues`

Convert Jira HTML, ADF, and wiki formatting into equivalent Markdown without changing visible content. Decode HTML entities, preserve link labels and destinations, and retain attachment references at their original positions. Preserve literal HTML snippets, SQL, HTTP messages, shell commands, JavaScript, and JSON request or response evidence as written, using inline or fenced code where appropriate. Technical evidence inside the ticket is content, not a transport wrapper. Do not store HTML used only for Jira formatting, ADF nodes, Jira wiki constructs, or Jira API-response envelopes.

Redact credentials, cookies, authorization headers, access tokens, signed URL query values, passwords, and secret values that appear in ticket text before writing the local archive. Replace only the secret value with `[REDACTED]`; keep the surrounding wording, field names, and technical syntax intact. Do not invent omitted values.

Before finishing, verify that:

- `ticket-<JIRA-KEY>.md` and one `duplicate-<DUPLICATE-JIRA-KEY>.md` for every distinct issue directly connected by a `Duplicate` link in either direction exist in the named issue's folder, with each file matching its retrieved issue;
- each file's first substantive section is the complete ticket-overview table;
- every non-empty current issue field and description paragraph is present in its own file in the source's wording and order, apart from formatting conversion and secret redaction;
- no comments or change history appear in any archive;
- each file contains readable Markdown and no Jira formatting tags, ADF, Jira wiki markup, or API-response wrapper;
- no unredacted credential-like values remain in any archive; and
- no archive claims attachments were downloaded when only their metadata was saved.
