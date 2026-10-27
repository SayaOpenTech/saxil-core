# Offline usage example

After obtaining and verifying the published 0.1.0 wheel, put it in a local
`wheels` directory and install without contacting an index:

```sh
python -m pip install --no-index --find-links=wheels saxil-core==0.1.0
```

Save this as `offline_roundtrip.py`:

```python
from saxil_core import SemanticFrame, decode, encode, validate

frame = SemanticFrame(speaker="user", act="ask", intent="query_price", polarity="pos", action="query")
packet = encode(frame)
assert decode(packet).intent == "query_price"
assert encode(decode(packet)) == packet
print(validate(packet))
```

Run it using the installed SDK:

```sh
python offline_roundtrip.py
python -m saxil_core version
```

The codec and CLI make no network calls. Obtaining the wheel initially requires
an online source or an existing verified copy; the separate two-service example
uses loopback HTTP by design. See [installation](INSTALLATION.md) and the
[example runner](../examples/README.md).
