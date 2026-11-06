---
name: appsec-poc-report
description: Create a shareable, chronological AppSec proof-of-concept Markdown report from saved HTTP evidence and screenshots.
disable-model-invocation: true
---

# AppSec PoC report

Use this skill only when the user explicitly invokes `$appsec-poc-report`. Turn an already performed, locally recorded security PoC into one evidence-backed Markdown report suitable for internal review, Git, and PDF export. This skill authorizes documentation and offline verification, not new target requests, Jira publication, or a Git commit.

## Inputs and output

Identify the ticket, the PoC evidence folder, the intended audience, and the report destination from the user's request and workspace. If no filename is given, write `<ticket-folder>/<short-poc-name>-report.md` outside Git-ignored raw-evidence folders. Keep the original requests, responses, and screenshots unchanged. Check applicable project instructions and `.gitignore` before writing.

## Evidence ledger

Read the ticket/assessment and every relevant preserved request, response, manifest, user-supplied artifact, and screenshot. For each step, record the action, actor or credential type, method and route, timestamp with timezone, observed status, decisive response fields, and source file. Verify pair provenance through Burp's pair metadata or explicit request-response wrappers; nearby bytes in a Burp project do not establish a pair. Recalculate hashes when a manifest provides them. Inspect screenshots visually and record only what they show.

Separate **captured HTTP results**, **screenshots**, **UI actions without retained HTTP transactions**, **inference**, and **unperformed checks**. A role name or UI control is not proof that every backend permission works. A response-only artifact does not establish its request headers. Explain any negative result or missing milestone that affects the chain.

## Write the report

Use [assets/poc-report-template.md](assets/poc-report-template.md) as the report structure. Keep its context, result, chronological numbered steps, evidence conclusion, and integrity sections; repeat or omit step blocks according to the actual PoC. Remove every template instruction and placeholder from the finished report. Do not copy facts from an earlier report into a new one.

Write in a direct, neutral voice appropriate for a report created by the person who performed the PoC. Do not refer to that person as “the tester,” “the researcher,” “the user,” or “they.” Prefer “The expected invitation email was not received” and “Password setup completed without an error” to third-person accounts. Do not add first-person narration unless the user requests it. Preserve evidence limits with factual wording such as “The reset transaction was not retained” or “The screenshots show the logged-in page.”

Open with the narrow demonstrated outcome and test context. Then document the PoC in chronological numbered sections: the action or redacted raw request, the observed response or other result, and the screenshots at the step they support. Use short, clearly labeled excerpts of actual response fields rather than copying large responses. Preserve exact routes, IDs, roles, counts, and times when they matter; distinguish selected fields from an exact full response. Finish with what the evidence establishes, what remains unproved, and an image/response integrity table when hashes are available. Do not claim a new vulnerability in an administrative endpoint merely because a disclosed admin credential was accepted there.

Make the report safe for its stated Git and sharing audience. Replace reusable Basic values, cookies, bearer tokens, passwords, reset links, signed URLs, and secret-bearing response fields with `[REDACTED]`; keep surrounding syntax. Never paste secrets into a command line, tool output, report, or script. Inspect each screenshot for visible secrets before inclusion. If one contains a secret, embed only a genuinely redacted derivative whose pixels no longer contain it, and retain the original separately. Assess unrelated personal and customer data against the stated audience and minimize it where necessary.

For a **single-file report with inline screenshots**, draft with placeholders in the form `{{INLINE_IMAGE:filename.png|Descriptive alt text}}`, then run `scripts/embed_images.py` with the report path and image-root directory. The helper embeds the original PNG/JPEG/WebP bytes as data images and prints only names, sizes, and SHA-256 values. Use redacted derivative files as inputs when redaction was required. Confirm that each image appears at the right point in the narrative and that the embedded bytes match its approved source. Data images support a self-contained Markdown source for suitable PDF renderers; Jira may require the images to be uploaded as attachments and inserted in its editor. Explain that distinction when the user intends to paste the report into Jira.

## Finish

Check that every action and result is traceable to its source, every screenshot is present, all local links resolve, the report is not Git-ignored when it is meant to be committed, and no credential material remains in text or embedded images. Check for remaining placeholders and third-person labels for the report's author. Verify the report's rendering when a renderer is available. Give the user the report path, the evidence limits, and any Jira image-handling step. Do not post or commit unless the user explicitly requests that separate action.
