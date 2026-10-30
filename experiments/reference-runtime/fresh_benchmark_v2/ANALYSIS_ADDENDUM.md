# Analysis clarification

Written before inspecting the final accuracy results. This analysis clarification
is not part of the original sealed inference protocol; the confidence intervals
are exploratory and do not change any inference or scoring rule.

- Independently rescore raw returned content against source records and requested
  role/label. Compare the independent score to the online runner's score.
- Treat 120 cases as the distinct test cases. Three inference seeds repeat those
  cases; 360 responses per arm are not 360 independent training replications.
- Compute correctness differences with a paired case-cluster bootstrap: average
  the three seed outcomes for each case, resample the 120 paired cases 10,000
  times using analysis seed 20261029, and report the 2.5/97.5 percentiles.
- Count parse, resolution, transport and missing-result failures in the primary
  denominator. Also report them separately.
- API latency is descriptive wall time under concurrency. Do not infer native
  inference speed, SDK performance or voice-agent end-to-end speed from it.
- The direct arm includes exact text; reference arms externalize it. The two
  reference arms share the same tables, decision information and resolver.
- No claim about native SAXIL tokens or reproduction of the historical 4B
  checkpoint follows from this hosted 9B test.
