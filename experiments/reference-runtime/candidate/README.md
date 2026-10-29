# SAXIL reference runtime — local research candidate

Status: unpublished `0.0.0.dev0`. This is a small new implementation motivated by
the VALUE_REF and ENTITY_SIDECAR audit. It has not reproduced the historical
model results, and it is not the historical native-token implementation.

The host stores exact text and entity names. A model selects a short reference.
The host checks the original request scope, generation, kind, semantic role,
value type and unit before retrieving that text. Values are strings so phones,
leading zeros and decimal spelling survive unchanged. This module preserves
spelling; it does not validate domain-specific prices, dates or phone numbers.

It has no required runtime dependencies, no model weights and no tokenizer.
It does not change W2, SAXIL_NATIVE_R2, or the public saxil-core package. Reference
metadata can also travel in JSON. No exclusive advantage over equivalent JSON
reference handling is claimed.

```python
from saxil_refs import Origin, TurnReferences, ValueRecord, ValueType

turn = TurnReferences("quote-123")
ref = turn.add_value(ValueRecord(
    ValueType.PRICE, "1234500", "quoted_price", Origin.TOOL_RESULT, "TOMAN"
))
# Retain this envelope at dispatch, before waiting for the model.
envelope = {"scope_id": turn.scope_id, "generation": turn.generation}
model_alias = ref.alias  # Illustrative model selection; no inference occurs here.
selected = turn.bind_selection(model_alias, **envelope)
value = turn.resolve_value(selected, expected_type=ValueType.PRICE,
                           expected_role="quoted_price", expected_unit="TOMAN")
assert value.exact_text == "1234500"
```

Populate tables only from semantic input, explicit session state or actual tool
results. The origin enum records a host assertion; it cannot prove that the host
did not copy a gold answer. Dataset provenance must be audited separately.

The host must define expected type/role/unit independently of model output.
Checking a role against an expectation copied from that same output adds no
semantic protection. A model can still select the wrong valid reference among
multiple records with the same type, role and unit. This API does not solve that.

Each table has an opaque scope. Reset increments its generation and invalidates
all old references even if slots are reused. Retain the original dispatch
envelope for late responses. A bare `VAL_E0` cannot establish which turn it came
from. Scope fields prevent accidental mixing; they are not network authentication
or protection against a caller with access to Python internals. Tables are not
thread-safe; the host owns synchronization and table lifetime.

Run checks from the candidate directory after installing in an isolated venv:

```text
python -m unittest discover -s tests -v
```

Release requirements remain open: approved source/data provenance; checksums and
identity for original training artifacts; governed model replay; corrected fresh
test corpus; a JSON baseline using the same references and guards; broader model
evaluation; and selection of the final package/API and publication scope.
This new runtime code is licensed under Apache-2.0; it bundles no model assets.
