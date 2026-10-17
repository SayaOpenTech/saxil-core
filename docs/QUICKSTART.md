# Quick Start

```python
from saxil_core import SemanticFrame, Ent, encode, decode

frame = SemanticFrame(
    speaker="user",
    act="ask",
    intent="query_price",
    polarity="pos",
    action="query",
    object=Ent(eid=1, typ="product", ref="this"),
)
wire = encode(frame)
restored = decode(wire)
assert encode(restored) == wire
print(wire.hex())
```

CLI:

```powershell
@"
{"type":"semantic","act":"ask","intent":"query_price","polarity":"pos","speaker":"user","action":"query"}
"@ | saxil encode --hex
```
