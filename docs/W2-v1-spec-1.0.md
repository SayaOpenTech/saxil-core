# SAXIL W2 Normative Specification — FINAL PROPOSAL (NOT ACTIVATED)

**SAXIL** = **Semantic Agent eXchange Intermediate Language**

| Field | Value |
|---|---|
| Document id (proposed frozen) | `W2-v1-spec-1.0` |
| Status | **READY_FOR_OWNER_APPROVAL / NOT ACTIVATED** |
| Wire / profile | `byte0 == 2` / `W2-v1` |
| Software version | **Orthogonal** — software SemVer (e.g. `0.1.0rc1` today; post-GO TBD by owner) is **not** a wire field and MUST NOT be confused with this specification id |
| Date | 2026-10-16 |
| Sources | Phase 3 DRAFT + Phase 5 FREEZE PROPOSAL + TECHNICAL_FREEZE_DECISION_PACKAGE; editorial cleanup only |
| Codec behavior change in this proposal | **NONE** |

Activation requires explicit owner approval to freeze this exact SHA-256. Until then this file is a proposal only.

---

## 0. Relationship to implementations

| Artifact | Role |
|---|---|
| This specification (`W2-v1-spec-1.0`) | Normative contract for interoperable Encoder/Decoder |
| `protocol/voice_extension/codec.py` (+ `ast.py`, `dicts.py`) | Reference implementation behavior for Core |
| `conformance/INDEPENDENT_CONFORMANCE_VECTORS.json` | Public machine-checkable vectors for Core MUST paths |
| Software package `saxil-core` | Delivers an implementation; its SemVer may advance without changing this Spec id |

Independent implementations MUST satisfy MUST / MUST NOT below. Matching Python module layout is IMPLEMENTATION_DETAIL.

---

## 1. Normative language

The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as in RFC 2119.

---

## 2. Layered identity

| Layer | Identifier | Notes |
|---|---|---|
| Software | SemVer product label (orthogonal) | Not a wire field |
| Protocol / wire | `byte0 == 2` | EXPLICIT_CONTRACT |
| Codec profile | `W2-v1` | SDK / Spec profile id |
| Spec document | `W2-v1-spec-1.0` | Frozen document id (when activated) |
| W1 | `byte0 == 1` | Separate; Core W2-only `decode()` MUST NOT accept as W2 |
| S0.1 / V0.1 / NATIVE_R2 | out of Core W2 scope | MUST NOT be claimed as W2 |

Historical draft labels such as software `0.1.0-dev` are **superseded as current software identifiers** and MUST NOT appear as the live software version for this freeze package. They may exist only in changelogs as history.

---

## 3. AST abstract types

### 3.1 SemanticFrame

**Required fields (MUST be present on encode):**

- `speaker` ∈ closed SPEAKER table
- `act` ∈ closed ACT table
- `intent` ∈ closed INTENT table
- `polarity` ∈ closed POLARITY table

**Optional fields (MAY be omitted):** `action`, `object` (Ent), `attribute`, `time` (Date|Time), `affect`, `qtype`, `request`, `cond` (Cmp), `known` (tuple[Ent]), `modality`, `uncertainty`.

### 3.2 Non-wire AST fields — EXPLICIT_CONTRACT

`modality` and `uncertainty` exist on the AST dataclass but are **not** carried on the current W2 wire.

- Encoders MUST NOT invent wire tags for `modality` / `uncertainty` under profile `W2-v1`.
- Decoders MUST NOT require them.
- Implementations MUST document that these fields are non-wire; round-trip of the full dataclass MAY lose them.
- A future profile or version byte is required before they may appear on the wire.

### 3.3 Ent / Num / Date / Time / Cmp / VerbalUtt / VUnit

As defined by the frozen reference `ast.py` / `dicts.py` for `W2-v1`. Numeric magnitudes use unsigned varint paths where applicable; string digit payloads use KIND_DIGITS. VerbalUtt `units` length MUST be in `1..MAX_SEQ`.

---

## 4. Wire format — EXPLICIT_CONTRACT

### 4.1 Packet header

```text
byte0: version = 2
byte1: msg_type = 0x10 (SEMANTIC) | 0x11 (VERBAL)
```

Decoders MUST reject other `byte0` values for W2-only decode with a version error.
Decoders MUST reject unknown `msg_type` under version 2.

### 4.2 Character encoding

UTF-8 MUST be used for open string literals. Closed enum tables use u8 indices on the wire.

### 4.3 Semantic body

```text
byte2: n_fields (u8)
repeat n_fields times:
  tag (u8)
  tag-specific payload
```

- Canonical field order (MUST): tags sorted ascending by tag numeric value before emission.
- Duplicate tags MUST be rejected on decode.
- Required tags: SPEAKER=0x01, ACT=0x02, INTENT=0x03, POLARITY=0x04 MUST all appear.
- `n_fields` MUST satisfy `4 <= n_fields <= MAX_FIELDS` (24).

### 4.4 Verbal body

```text
byte2: utt_type enum u8
byte3: n_units (u8), 1..MAX_SEQ
repeat n_units: unit opcode + payload
```

Trailing garbage after the last unit MUST be rejected.

### 4.5 Limits (Core MUST enforce)

| Limit | Value |
|---|---:|
| MAX_PACKET | 4096 |
| MAX_LITERAL | 96 |
| MAX_SEQ | 64 |
| MAX_FIELDS | 24 |
| MAX_NEST | 8 |
| known entities | ≤ 8 |

### 4.6 Varint

Unsigned LEB128, max 5 bytes / uint32 range.

---

## 5. Closed tables

Enum membership is defined by frozen `dicts.py` ordering for `W2-v1`.
Index assignment MUST be stable. Unknown enum indices MUST be rejected (or map to documented absent sentinels where tables include empty-string sentinels).

**This proposal defines no new Tag, Opcode, or Enum ID.**

---

## 6. Canonicalization — EXPLICIT_CONTRACT

For any AST `x` accepted by the Encoder:

1. `encode(x)` MUST be deterministic.
2. `encode(decode(encode(x)))` MUST equal `encode(x)`.
3. The byte string from (1) is the **canonical encoding**.

---

## 7. Errors — EXPLICIT_CONTRACT

Invalid inputs MUST NOT be silently repaired into a different valid message.
W2-only decode of version 1 MUST fail closed (version error).

---

## 8. Compatibility

- W1 packets: MAY be decoded via a combined `decode_any` entry point; MUST NOT be returned by W2-only `decode`.
- Unknown tags: current decoder MUST reject (fail-closed).

---

## 9. Out of scope

Persian S0.1/V0.1 text, Native token IDs, model inference, transport envelopes beyond raw W2 bytes, STT/LLM/TTS.

---

## 10. Freeze criteria

This proposal MAY be activated as frozen `W2-v1-spec-1.0` only when the owner explicitly approves the exact SHA-256 of this file (or a byte-identical successor authorized by the owner), and independent conformance vectors cover Core public MUST paths.

## 11. No binary behavior change certificate

Compared to the Phase 5 freeze proposal body and the validated RC codec:

- No new wire tags
- No new opcodes
- No LEX / INTENT / ACTION reorder
- No AST structural change
- No encode/decode semantic change

Editorial changes in this proposal are limited to status framing, layered identity clarity, removal of stale `0.1.0-dev` as *current* software id, and explicit non-wire rules for modality/uncertainty.
