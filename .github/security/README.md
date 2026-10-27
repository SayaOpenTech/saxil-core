# ADOPT-04: repository security assessment

Scope: security policy, dependency-update configuration, and optional static
analysis for the public repository only. This proposal does not change repository
settings, the W2 specification, SDK/API behavior, versions, or published artifacts.

## Live baseline (2026-10-27 UTC)

Inspected upstream `main` at
[`2de488598affe85cdc27d68f300baedd9d29791c`](https://github.com/SayaOpenTech/saxil-core/commit/2de488598affe85cdc27d68f300baedd9d29791c).
The requirements come from [Issue #4](https://github.com/SayaOpenTech/saxil-core/issues/4).

| Control | Read-only GitHub evidence | Result |
| --- | --- | --- |
| Security policy / Dependabot config | Recursive Git tree at the baseline commit | No `SECURITY.md`, Dependabot config, or static scanning workflow |
| Private Vulnerability Reporting (PVR) | `GET /repos/SayaOpenTech/saxil-core/private-vulnerability-reporting` | `enabled: false` |
| Dependabot alerts | `GET .../vulnerability-alerts`; `GET .../dependabot/alerts?per_page=100` | HTTP 204 (enabled); empty alert list at inspection time |
| Dependabot security updates | Repository `security_and_analysis.dependabot_security_updates` | `disabled` |
| CodeQL default setup | `GET .../code-scanning/default-setup` | `state: not-configured`; detected languages `actions`, `python` |
| Code scanning analyses | `GET .../code-scanning/alerts?per_page=100` | HTTP 404, `no analysis found`; not a clean security scan |
| Secret scanning / push protection | Repository `security_and_analysis`; secret-scanning alerts endpoint | Both `disabled`; alerts endpoint explicitly returned disabled (404) |
| Existing workflows | `GET .../actions/workflows` and workflow source at baseline | Active Public CI and Publish to PyPI workflows; no security scanner |

These observations are a dated snapshot, not a guarantee that the repository or
its dependencies have no vulnerabilities. The CLI also emitted a scope hint for
the code-scanning 404; no permission was added and no stronger absence claim is
made from that error. Alert payloads and secrets are not copied into this report.

## Proposed source changes

- `SECURITY.md` explains scope, private disclosure, sanitized reproductions, and
  best-effort handling without an invented contact, SLA, bounty, or patch promise.
  `CONTRIBUTING.md` links to it.
- `.github/dependabot.yml` schedules weekly GitHub Actions and public pip updates
  with at most five open version-update PRs per ecosystem. It uses the default
  branch and no private registries, secrets, assigned contacts, or auto-merge.
  The pip entry covers `pyproject.toml` build/dev requirements and the scanner
  requirements file. The SDK has no mandatory runtime dependencies. Broad lower
  bounds already allowing current versions may produce no manifest change;
  this config is not a lockfile or a dependency-vulnerability audit.
- `Security checks` runs Bandit 1.9.4 from a separate tooling requirements file on
  public `src/` at PRs to main, main pushes, weekly schedules, and manual dispatch.
  Actions use the already-reviewed full commit pins, read-only `contents`, no
  persisted checkout credentials, no secrets/OIDC/environment, and a timeout.
  Fork/Dependabot PRs use `pull_request`, never `pull_request_target`.

Bandit parses Python syntax without installing/executing the SDK. The gate fails
on findings with **both severity and confidence at least medium**, with no rule
skips, baseline suppressions, or `continue-on-error`. Lower-rated findings are
outside this initial gate. Tests, release tooling, and workflow YAML are outside
the scan target. This does not prove W2 semantic correctness, resistance to all
malformed inputs, dependency safety, or absence of secrets. Existing conformance
and negative-input tests remain relevant. Do not change frozen code merely to
silence a scanner.

Bandit is selected as a small initial Python check that needs no administrative
change. **CodeQL is deferred**: it offers deeper analysis of Python and Actions,
but requires a separate decision about setup type, analysis scope and result-upload
permissions. Do not silently enable default setup or add competing workflows.
**Secret scanning and push protection are recommended for separate owner review**;
Bandit does not replace them. Dependency auditing (for example, pip-audit) is also
deferred: this project has no runtime dependencies, and an audit of resolved
build/dev tooling needs a clearly defined environment and triage policy.

## Outstanding owner decisions and verification

Issue #4 requires an owner-approved reporting channel. None was confirmed by the
issue (no comments) or the inspected policy/contributing files; PVR was disabled.
**This prerequisite remains unresolved.** The proposed policy therefore describes
only a conditional private form and a public request for a private channel with
no vulnerability details. Keep the PR draft until the owner confirms the channel
and reviews the wording. Do not mark Issue #4 complete solely because a PR exists.

Recommended next administrative decision: approve and enable PVR, or provide an
explicitly approved alternative private channel. After any separately authorized
PVR change, read back `enabled: true`, verify that the private reporting form is
available, and update the policy's current-channel wording through review. Do not
submit a fake vulnerability report as a test. There is no enablement in this PR.

Separately consider enabling Dependabot **security updates**, secret scanning and
push protection. Dependabot alerts are already enabled. The version-update config
does not itself enable security updates. After merge, inspect Dependabot update
jobs/PRs and scheduled Bandit runs; their operation cannot be proved from an
unmerged branch. New checks are not made required in branch rules by this PR.

To reproduce the proposed source scan in an isolated environment:

```sh
python -m pip install -r requirements-security.txt
python -m bandit -r src --severity-level medium --confidence-level medium
```

Review the PR's Actions results for the exact tested commit. A local package
download timed out during preparation; that failed installation is not a passing
scan. Never rebuild or publish 0.1.0 to validate this change. Roll back source
changes through a new reviewed PR; this proposal has no settings to roll back.

## Primary references

- [GitHub: privately reporting a vulnerability](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately)
- [GitHub: configuring PVR](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [GitHub: Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [GitHub: advanced code scanning setup](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning)
- [Bandit: command-line options and thresholds](https://bandit.readthedocs.io/en/latest/man/bandit.html)
- [Bandit 1.9.4 package](https://pypi.org/project/bandit/1.9.4/)
