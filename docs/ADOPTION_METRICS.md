# Community feedback and adoption evidence

## Feedback channels

The owner's approved public project channels are this repository's
[Issues](https://github.com/SayaOpenTech/saxil-core/issues) and
[pull requests](https://github.com/SayaOpenTech/saxil-core/pulls). Use the bug,
usage-question or proposal form; blank issues remain available, including a
request for a private reporting channel without vulnerability details.

Suspected vulnerabilities use the approved private PVR channel in
[SECURITY.md](../SECURITY.md). No new email, chat service, contact address or
response SLA is designated. Contributions follow the DCO and scope in
[CONTRIBUTING.md](../CONTRIBUTING.md).

For public triage, first reproduce against the stated SDK version, distinguish
installation/docs/application-boundary problems, and link duplicates. Record the
resolution or remaining limitation with evidence. Do not promise a delivery date,
new protocol or release merely because an issue was filed.

## Indicators and their limits

| Indicator | Definition and source | Interpretation limits |
| --- | --- | --- |
| PyPI downloads | Aggregate download events for normalized project `saxil-core`, with retrieval date, exact date window and mirror policy recorded | Events are not unique people, installations, active users or successful use. CI, bots, caches and mirrors distort counts. Our own example/benchmark workflows also download the package. |
| User issues | Distinct public bug/usage/use-case reports in a defined period; distinguish roadmap/maintainer work and bots | Volume can indicate friction, not adoption or product quality. Never count a PR again as an issue. |
| Contributions | Public PRs by humans outside the maintainer group, with reviewed/merged counts separately | Exclude Dependabot, GitHub Actions and first-party roadmap PRs from independent contributions. A PR is not proof of deployment. |
| Independent usage | A dated public reference or consented report from someone outside the project that identifies a concrete use case and reproducible integration | Require evidence; do not infer it from stars/downloads. This project's own examples and ADOPT-10 demo are first-party demonstrations. |
| Stars/forks | Optional aggregate interest signals from the repository API | They do not establish use, endorsement, production readiness or active users. |

GitHub's repository `open_issues_count` includes pull requests; use searches with
`is:issue` and `is:pr` to separate them. Categorize authors/automation explicitly
and retain public links rather than inferring identity from a display name.

## Collection method

Use a small manual, aggregate-only snapshot when reviewing adoption. Record:

1. Observation date/time in UTC, source URL/query and data window.
2. Project/version scope and inclusion/exclusion rules.
3. Counts, response availability and any anomaly. Use **unverified/unavailable**,
   not zero, for a failed or inconsistent response.
4. Public evidence links and a separate first-party/independent classification.
5. The interpretation and limitations; do not add overlapping rolling windows.

For example, repository interest counts can be read without downloading user data:

```sh
gh api repos/SayaOpenTech/saxil-core --jq '{stargazers_count,forks_count}'
```

[PyPI Stats' API](https://pypistats.org/api/) exposes aggregate `/recent` and
`/overall` endpoints. Data updates daily; cache responses and query the same
endpoint at most once per day. For `/overall`, record `mirrors=false` when using
the without-known-mirrors series. Do not sum last-day/week/month rolling totals.
Inspect window consistency before using a snapshot. A preparation-time `/recent`
response had inconsistent weekly/monthly totals and was not accepted as a
verified adoption count.

The [PyPA download-analysis guide](https://packaging.python.org/en/latest/guides/analyzing-pypi-package-downloads/)
describes the public aggregate-data approach and cache/mirror limitations.
No cloud account, paid query service or new analytics provider is configured by
this task. Do not claim independent adoption merely from the infrastructure and
examples added by this roadmap.

## Privacy and baseline

No SDK telemetry, tracking pixel, analytics script, device identifier, IP log
collection or per-user event pipeline is added. This method uses existing public
aggregates and voluntary public/consented usage evidence. Do not publish private
reports, customer names, emails, raw traffic logs or identifying user data.

At this task's completion, **no independent external usage has been verified by
this work**. Downloads are not assigned a verified baseline because the retrieved
rolling-window response was inconsistent. This is an evidence status, not a
claim that nobody uses the package. Future snapshots should preserve the same
definitions so changes remain interpretable.
