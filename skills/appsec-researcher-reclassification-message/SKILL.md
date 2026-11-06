---
name: appsec-researcher-reclassification-message
description: Write a factual message explaining a security severity reclassification to the reporting researcher.
---

# AppSec researcher reclassification message

Write a researcher-facing message that explains why a vulnerability severity changed after assessing its actual impact in the affected environment.

The output is a communication message, not an internal assessment report.

## Inputs

Use the supplied vulnerability report, investigation evidence, confirmed environment facts, permission findings, business context, original severity, and final severity.

Read the available source material before drafting. Build a fact set containing:

- The confirmed vulnerability and affected component.
- The access or role required for exploitation.
- The confirmed data type and sensitivity.
- The confirmed business importance and scope of the affected component.
- The effective cloud, platform, or application permissions that were checked.
- The confirmed security impact that remains.
- The original and final severity.

If the facts do not support the proposed severity, state the conflict instead of writing a misleading justification.

## Evidence boundary

Use only direct test results and confirmed environment or permission facts.

State a capability is absent only when the relevant configuration, policy, or control was checked. An untested outcome is not evidence that the capability is unavailable.

Keep these items out of the message:

- Speculative attack paths.
- Remaining investigation questions.
- Claims based only on tests that were not performed.
- Names of internal responders or teams.
- Statements that engineering was consulted.
- Internal investigation steps or evidence-gathering methods.
- Local files, internal notes, or internal ticket history.
- Exact internal resource identifiers discovered after the original report, unless the user asks to disclose them or they are needed to explain the decision.
- Remediation instructions, unless the user requests them.

Write the confirmed facts directly. The researcher does not need to know who supplied each fact or how AppSec obtained it.

## Severity reasoning

Treat a taxonomy or VRT priority as the initial baseline when that is how the original rating was assigned. Explain that the final severity reflects the confirmed impact in the actual business environment.

Show both sides of the decision:

- Acknowledge why the vulnerability remains security-relevant.
- Explain which confirmed facts limit its likelihood, scope, data sensitivity, permissions, or business impact.

Do not minimize the report or argue against the vulnerability class. Explain why the confirmed environment fits the final severity better than the original severity.

## Writing rules

- Address the reporting researcher directly and respectfully.
- Use simple English and short sentences.
- Keep the vulnerability summary brief.
- Use four to eight bullets for the facts that drive the decision.
- Include only facts needed to explain the reclassification.
- Describe internal resources at the level needed for the severity decision, such as "service-related storage" or "a limited reporting subsystem."
- Distinguish customer data from credentials, platform permissions, and other system access.
- End with the final severity and one clear sentence explaining why it fits.
- Keep the message between roughly 180 and 350 words unless the user requests another length.

## Output structure

```markdown
Hi [researcher],

Thank you for reporting this vulnerability. We confirmed <brief vulnerability summary>.

The original <severity> rating followed <the applicable baseline, if confirmed>. After assessing the actual impact in this environment, we determined that <final severity> is more appropriate.

The confirmed facts that informed this decision are:

- <Required access or exploit condition.>
- <Affected component and business importance.>
- <Data type and sensitivity.>
- <Confirmed permission limitation.>
- <Confirmed permission limitation.>
- <Security impact that remains.>

<Closing paragraph acknowledging the serious impact while explaining why the confirmed scope fits the final severity rather than the original rating.>
```

Do not force every placeholder into the output. Merge overlapping facts and remove bullets that do not help explain the decision.

Completion means the message is ready to send to the researcher, contains only necessary confirmed facts, does not expose internal investigation details or newly discovered resource identifiers, acknowledges the remaining security impact, and clearly explains why the final severity fits the affected environment.
