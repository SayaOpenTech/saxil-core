# Known Limitations

1. **Public Core under Apache-2.0** — brand/trademark rights in Saya/SAXIL remain separate from the code license.
2. **W2-only Core** — S/V and Native profiles deferred.
3. **No NLU** — cannot turn free Persian ASR text into W2 without gold/research adapters; free-text Persian is **not** automatically reversible via W2.
4. **No LLM interpretation** — a generic LLM does not “speak SAXIL” without dedicated integration / fine-tuning; readable S0.1 is *more* expensive under frozen Qwen tokenization (audit evidence).
5. **Benchmark claims** — W2 byte compression vs Persian on gold is historically supported; universal token/$ savings are **not** claimed by this SDK. No end-to-end Voice Agent acceleration is claimed.
6. **CLI JSON AST** covers common fields; exotic nested attributes may need the Python API directly.
7. Vendored `protocol.voice_extension.__init__` omits research `map_gold` (intentional packaging difference; codec modules remain byte-identical).
8. **Modality / uncertainty** — present on the AST dataclass but **not** emitted on the W2 wire in this profile.
9. **Platforms** — tested on Windows + Python 3.13 and WSL Ubuntu + Python 3.12; other Linux/macOS hosts remain NOT_VERIFIED as support SLA.
10. **Normative Spec** — `W2-v1-spec-1.0` is owner-approved and frozen; see `docs/W2-v1-spec-1.0.md` and `W2-v1-spec-1.0_FREEZE_DECISION.json` (hashed Spec body is immutable).
