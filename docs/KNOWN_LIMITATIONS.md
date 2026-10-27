# Known Limitations

1. **Public Core under Apache-2.0** — brand/trademark rights in Saya/SAXIL remain separate from the code license.
2. **W2-only Core** — S/V and Native profiles deferred.
3. **No NLU** — applications must map their own input into supported structured AST values; free-text Persian is **not** automatically reversible via W2.
4. **No built-in LLM interpretation** — the SDK does not teach a model to interpret W2. Integrations must define how structured data is produced and consumed.
5. **Benchmark claims** — encoded size and throughput depend on the inputs and comparison representation. This SDK claims no universal token/cost savings or end-to-end voice-agent acceleration. Private research results are not public SDK benchmark evidence.
6. **CLI JSON AST** covers common fields; exotic nested attributes may need the Python API directly.
7. Vendored `protocol.voice_extension.__init__` omits research `map_gold` (intentional packaging difference; codec modules remain byte-identical).
8. **Modality / uncertainty** — present on the AST dataclass but **not** emitted on the W2 wire in this profile.
9. **Platforms** — [public CI](https://github.com/SayaOpenTech/saxil-core/actions/workflows/ci.yml) tests Linux and Windows with Python 3.10–3.13. The declared Python minimum does not verify all newer versions or other platforms. No support SLA is promised.
10. **Normative Spec** — `W2-v1-spec-1.0` is owner-approved and frozen; see `docs/W2-v1-spec-1.0.md` and `W2-v1-spec-1.0_FREEZE_DECISION.json` (hashed Spec body is immutable).
