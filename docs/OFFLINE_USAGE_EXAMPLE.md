# Offline Usage Example

No network calls are made by the codec or CLI.

```powershell
# After local wheel install (no index):
python -m pip install --no-index --find-links=<path-to-dist> saxil-core

python - <<'PY'
from saxil_core import SemanticFrame, encode, decode, validate
fr = SemanticFrame(speaker="user", act="ask", intent="query_price", polarity="pos", action="query")
b = encode(fr)
assert decode(b).intent == "query_price"
print(validate(b))
PY

saxil version
```
