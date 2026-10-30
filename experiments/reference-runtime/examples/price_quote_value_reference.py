"""Resolve an exact host-owned price after an illustrative model selection.

This example exercises the reference runtime only. ``model_response`` is a
fixture; no model inference, W2 encoding, quote acceptance, or payment occurs.
"""
from saxil_refs import Origin, ReferenceError, TurnReferences, ValueRecord, ValueType


def main() -> None:
    # Public synthetic tool results. Keep the exact amount in host-owned state.
    quotes = [
        {"label": "standard delivery", "amount": "1,250,000", "unit": "TOMAN"},
        {"label": "pickup discount", "amount": "1,199,000", "unit": "TOMAN"},
    ]

    turn = TurnReferences("demo-quote-42")
    for slot, quote in enumerate(quotes):
        turn.add_value(
            ValueRecord(
                ValueType.PRICE,
                quote["amount"],
                "selected_quote",
                Origin.TOOL_RESULT,
                quote["unit"],
            ),
            slot=slot,
        )

    # Save these when dispatching the model request. A late response must use
    # its original envelope so a reset turn cannot revive an old alias.
    dispatch = {"scope_id": turn.scope_id, "generation": turn.generation}

    # Stand-in for the model response: in a live application this is returned
    # by the model after seeing the permitted quote descriptions/references.
    model_response = {"selected_price_ref": "VAL_E1"}

    reference = turn.bind_selection(model_response["selected_price_ref"], **dispatch)
    selected = turn.resolve_value(
        reference,
        expected_type=ValueType.PRICE,
        expected_role="selected_quote",
        expected_unit="TOMAN",
    )
    assert selected.exact_text == quotes[1]["amount"]
    print(f"selected={reference.alias}")
    print(f"exact_price={selected.exact_text} {selected.unit}")

    # Unknown aliases fail closed; they never fall back to another quote.
    try:
        turn.bind_selection("VAL_E7", **dispatch)
    except ReferenceError as error:
        assert error.code == "unknown_reference"
        print("unknown_alias=REJECTED")
    else:
        raise AssertionError("unknown reference unexpectedly resolved")


if __name__ == "__main__":
    main()
