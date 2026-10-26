# PyPI publishing proposal (ADOPT-03)

This PR is a source proposal, not publication authorization. Do not merge or enable
production publishing until the owner approves the administrative settings below.
No version is currently approved for publication. The only manifest is the
immutable, verification-only 0.1.0 baseline; no release asset is rebuilt.

## Current audit and risks

- **High:** `pypi` has no protection rules, no deployment ref restriction, and
  `can_admins_bypass=true`. A matching trusted workflow can reach OIDC without
  a separate deployment approval. Main's PR/CI rules do not protect release tags
  or the environment.
- **High:** the existing publish job gives OIDC access to all of its download,
  shell and checksum steps. Separate verification from credential-bearing work.
- **Medium:** both `release: published` and unrestricted manual dispatch can
  reattempt 0.1.0 publication. A failed/retried upload is not an authorization gate.
- **Medium:** the PyPA action uses a movable `release/v1` reference; pin reviewed
  action commits. Existing fixed wheel/sdist hashes are a useful integrity control.
- **UNVERIFIED:** current private PyPI Trusted Publisher registrations, their
  environment binding, other publishers and API-token grants. GitHub API access
  cannot prove these absent. Public PyPI provenance proves the historical publisher
  workflow/commit and hashes, not the current private authorization configuration.
- Actions default to read permissions; all actions are permitted and SHA pinning is
  not required globally. Both ADOPT-02 main rulesets are active and unchanged.

## Proposed flow

PRs touching publishing files run verification only. Manual dispatch defaults to
`verify-only`. There are no release/push/PR-target publishing triggers. Inputs are
passed as environment data, not interpolated into shell source.

The read-only verifier uses only the standard library and GitHub CLI. It checks a
reviewed manifest, canonical version/tag, resolved tag commit, Release and asset
IDs/digests, source project/version, frozen specification, wheel/sdist metadata,
SHA256SUMS and independent file hashes. It never executes source/package code.
Existing PyPI hashes must match on verification runs. Publishing rejects ANY
existing PyPI version; only HTTP 404 means absent. Network errors fail closed.

`v0.1.0` is independently forbidden in publish mode, even if its manifest changes.
The publish job also excludes it. No new version approval is included in this PR.
Publication additionally requires dispatch from upstream main, an exact
`PUBLISH vX.Y.Z` phrase, admin/maintain permission for both original and rerun actor,
and repository variable `PYPI_PUBLISH_ENABLED=true` (currently absent).

Only the dedicated publish job requests `id-token: write` and references `pypi`.
It downloads the immutable artifact ID from its own verification job, then invokes
the pinned PyPA action with attestations and `skip-existing=false`. Verification
and evidence artifacts are separate, so evidence cannot be uploaded as a package.
Concurrency serializes the same tag without cancellation. PyPI still arbitrates
external publisher races; a concurrent upload fails rather than being skipped.

## Future versions and provenance contract

1. Obtain separate version/release/publication authorization; leave 0.1.0 unchanged.
2. Use a reviewed build workflow to build a new version once, without PyPI access.
   This PR does not create a build workflow or rebuild the legacy version.
3. Publish those approved assets to a new GitHub Release with SHA256SUMS.
4. Submit an approval manifest in a separate protected-main PR. It must bind version,
   tag, full source commit, numeric Release ID, both asset IDs and SHA-256 values,
   `publish_allowed: true`, and `build` with numeric `run_id`, exact `workflow_path`
   and `artifact_name`. The build artifact must contain exactly the wheel and sdist.
5. The verifier requires a successful same-repository push/manual build run at the
   exact source commit and approved workflow path, downloads its artifact, and
   compares both hashes against the Release/manifest. Expired/missing artifacts fail.
6. Run verify-only first, review the saved evidence, then obtain environment approval
   for the separately authorized manual publication. No publication is authorized now.

Evidence JSON binds the approval digest, source/tag/Release, build run, workflow
commit, run ID/attempt, artifacts and pre-publication PyPI state. Retain it outside
Actions before its 90-day expiry. For a future publication, record the publish run,
PyPI file hashes and PyPI attestations afterwards in the release issue. A PyPI
publish attestation identifies the publishing workflow commit (main); the approved
build record separately links package source. This is traceability, not a claim of
bit-for-bit reproducible builds or an independent security review of build code.

## Exact administration proposal — separate owner approval required

Do not apply these settings as part of this PR preparation:

- GitHub environment `pypi`: required reviewer User `xwpedram` (ID 20116710),
  `prevent_self_review=false` for the current single maintainer, wait timer 0,
  `can_admins_bypass=false`. One person deliberately dispatches and approves; this
  is an explicit second action, not independent two-person review. Enabling
  prevent-self-review would lock out the sole maintainer.
- Environment deployment policy: `protected_branches=false`,
  `custom_branch_policies=true`; exactly one custom policy with type `branch`,
  name `main`, and no tag policy. The workflow dispatch runs from protected main
  and verifies a release tag as data, so tags cannot select old workflow code.
- PyPI project `saxil-core`: inspect/export the private publisher inventory first.
  Expected sole GitHub publisher tuple: owner `SayaOpenTech`, repository
  `saxil-core`, workflow filename `publish-pypi.yml`, environment `pypi`.
  Review unexpected publishers/tokens with the owner; do not remove them blindly.
- Keep repository variable `PYPI_PUBLISH_ENABLED` absent or `false` until the owner
  has approved and verified the above AND a future version's publication. Setting
  it to `true` is a separate administrative operation; nothing sets it in this PR.
- Consider a separately approved tag ruleset preventing release-tag updates/deletion
  and restricting new version tags to the maintainer. Do not alter v0.1.0 or the
  existing main rulesets. No tag ruleset is created here.

Suggested environment PUT payload (review only):

```json
{
  "wait_timer": 0,
  "prevent_self_review": false,
  "reviewers": [{"type": "User", "id": 20116710}],
  "can_admins_bypass": false,
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  }
}
```

Then, only after approval, add the deployment policy `{"name":"main","type":"branch"}`.
Back up each response and read it back before any future publication.

## Rollback

Before a future administrative change, export environment settings, custom ref
policy IDs, variable state, and the private PyPI publisher inventory. Current
environment baseline is no protection rules, null ref policy, admins can bypass;
repository and environment variable inventories are empty.

If a new pipeline is faulty, first cancel any pending publication and set the enable
variable to `false` with owner approval. Keep environment protections and main
rulesets. Fix/revert source by a new PR, never a direct push. Do not restore the old
automatic 0.1.0 workflow as a live recovery path. If restoring an administrative
setting is necessary, restore only that setting from its export after explicit
approval; do not delete/recreate the environment or alter unrelated security rules.
Restore publisher entries only from the reviewed export. Already-published files
cannot be rolled back by retrying, deleting, rebuilding or retagging 0.1.0.

## Official guidance

- [PyPI: using a publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [PyPI: security model](https://docs.pypi.org/trusted-publishers/security-model/)
- [PyPI: adding a publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [GitHub: managing environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

The proposal follows PyPI's guidance on job-scoped OIDC, a dedicated environment,
and a minimal publishing job. PyPI examples show automatic release triggers; this
project deliberately uses explicit manual authorization instead.
