# Security policy

## Scope and versions

Security reports are welcome for SAXIL Core's public Python SDK, CLI, W2 binary
encoder/decoder, validation, and repository build/release tooling.

The current published version is **0.1.0**. Include the affected version and, for
source checkouts, the commit SHA. Reports about 0.1.0 and the current public `main`
branch can be assessed on a best-effort basis. This is not a promise of a patch,
backport, response deadline, or support service-level agreement.

Private research components and third-party applications are outside this
repository's scope. Published 0.1.0 artifacts and the frozen W2 specification are
immutable; any remediation requiring a new release needs separate authorization.

## Reporting a suspected vulnerability

**Do not put vulnerability details, exploit code, secrets, or sensitive data in a
public issue, pull request, discussion, or workflow log.**

The owner-approved reporting channel is **GitHub Private Vulnerability Reporting**
for this repository. It was enabled and verified on 2026-10-27.

1. Check the repository's [security advisories page](https://github.com/SayaOpenTech/saxil-core/security/advisories).
   Select **Report a vulnerability** and use that private form.
2. If the private form is unavailable, open a [public issue](https://github.com/SayaOpenTech/saxil-core/issues/new)
   containing only a request such as: "Please provide a private channel for a
   security report." Do not include the affected component, reproduction steps,
   impact, payload, or any other vulnerability details. Wait for maintainers to
   confirm a private channel before sharing them.

No security email address or alternative private contact is designated here.
The public request above is only a fallback to request a private channel if the
form becomes unavailable; it is not a vulnerability report.

## Information to provide privately

In the private reporting form, include:

- Affected package version or commit, Python version, and operating system.
- Expected and observed behavior, impact, and relevant trust boundaries.
- Minimal reproduction steps and a small, sanitized input if needed.
- Any proposed mitigation and your disclosure/credit preferences.

Use synthetic examples. Do not include credentials, personal data, private
research files, or data you are not authorized to share. Test only systems and
data you are authorized to assess.

Maintainers will assess reports and coordinate remediation and disclosure on a
best-effort basis. There is no guaranteed response or remediation timeline and
no bug bounty commitment. Please coordinate public technical disclosure through
the confirmed private channel.
