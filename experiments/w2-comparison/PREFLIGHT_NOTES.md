# Input-domain preflight before measurement

No size or timing experiment had run and no corpus/seal existed at this point.
The first generator attempt failed on an invalid entity ID. Published W2 accepts
IDs 1..255. The generator was corrected to stay within that documented domain.

Source inspection also showed that W2 Num strings strip non-digit characters;
an arbitrary decimal spelling is not losslessly supported. The draft decimal
family was replaced with an explicitly digit-only string family, preserving
leading zeros. This limits the claim rather than changing the SDK. The original
draft protocol is retained as PRE_REGISTERED_PROTOCOL-v0-before-api-preflight.json.

No invalid case was filtered out after seeing payload-size or timing results.
All 4,608 final cases must pass every-field equivalence before measurement.
