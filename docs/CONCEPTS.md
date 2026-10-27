# W2 and application boundaries

SAXIL Core encodes **already structured** messages. An application chooses
supported `SemanticFrame` fields or `VerbalUtt` units, calls `encode`, transports
the resulting bytes, and calls `decode` at the receiving end.

```text
Application data -> supported AST -> W2 bytes -> application transport
                                                |
Receiving application <- supported AST <- decode
```

W2 is the binary representation, not the transport, an intent extractor, a model
tokenizer, or a learned language interface. The HTTP framing in the executable
examples belongs to the example application.

## Canonical bytes

For supported data, `encode(decode(encode(frame))) == encode(frame)`. This
describes wire bytes. It does not preserve AST attributes absent from W2-v1,
including `modality` and `uncertainty`. The codec uses a closed vocabulary and
rejects unsupported values rather than guessing a natural-language meaning.

## Versions

Package version `0.1.0`, wire version byte `2`, profile `W2-v1`, and normative
document `W2-v1-spec-1.0` identify different layers. Changing docs or examples
does not change those identifiers or authorize another package publication.

See [compatibility](VERSION_PROFILE_COMPATIBILITY.md), the [AST contract](W2_AST_CONTRACT.md),
[limitations](KNOWN_LIMITATIONS.md), and [executable examples](../examples/README.md).
