# W2 AST Contract

Source of truth: vendored `protocol.voice_extension.ast` + `codec` in this package.

## Wire

- Version byte `byte0 == 2` (`W2_VERSION`)
- Message types: `MSG_SEMANTIC = 0x10`, `MSG_VERBAL = 0x11`
- Limits: `MAX_PACKET=4096`, `MAX_LITERAL=96`, `MAX_SEQ=64`, `MAX_FIELDS=24`, `MAX_NEST=8`

## SemanticFrame (required)

`speaker`, `act`, `intent`, `polarity` plus optional roles (`action`, `object`, `attribute`, `time`, …).

## VerbalUtt

`utt_type` + ordered `VUnit` sequence (`op` in LEX/NUM/CUR/DATE/TIME/NAME/ACR/PRON/PAUSE/EMPH).

## Canonicalization

`encode(decode(encode(x))) == encode(x)` for supported AST objects.  
The encoder output is the canonical byte form (`canonical_bytes`).

## Not in this contract

Persian text identity, S0.1/V0.1 strings, native token IDs, model logits.
