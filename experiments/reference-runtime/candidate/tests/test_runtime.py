import json
import unittest
from dataclasses import FrozenInstanceError

from saxil_refs import EntityRecord, Origin, Reference, ReferenceError, TurnReferences, ValueRecord, ValueType


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.table = TurnReferences("quote-1")
        self.price = ValueRecord(ValueType.PRICE, "001234.500", "quoted_price", Origin.TOOL_RESULT, "TOMAN")
        self.ref = self.table.add_value(self.price, slot=0)

    def resolve(self, ref=None, **overrides):
        args = dict(expected_type=ValueType.PRICE, expected_role="quoted_price", expected_unit="TOMAN")
        args.update(overrides)
        return self.table.resolve_value(ref or self.ref, **args)

    def error(self, code, fn):
        with self.assertRaises(ReferenceError) as caught:
            fn()
        self.assertEqual(caught.exception.code, code)

    def test_exact_text_survives_json_transport(self):
        received = Reference.from_dict(json.loads(json.dumps(self.ref.to_dict())))
        self.assertEqual(self.resolve(received).exact_text, "001234.500")

    def test_model_alias_uses_original_request_envelope(self):
        selected = self.table.bind_selection("VAL_E0", scope_id=self.ref.scope_id, generation=self.ref.generation)
        self.assertEqual(self.resolve(selected), self.price)

    def test_unknown_alias_is_rejected(self):
        self.error("unknown_reference", lambda: self.table.bind_selection("VAL_E7", scope_id=self.ref.scope_id, generation=self.ref.generation))

    def test_alias_spelling_cannot_coerce(self):
        for alias in ("VAL_E00", "val_e0", "VAL_E-1", "VAL_E0 ", "VAL_E0\n", "VAL_E" + "9" * 5000, 800, None):
            with self.subTest(alias=alias):
                self.error("invalid_alias", lambda: self.table.bind_selection(alias, scope_id=self.ref.scope_id, generation=self.ref.generation))

    def test_duplicate_slot_does_not_overwrite(self):
        self.error("duplicate_slot", lambda: self.table.add_value(self.price, slot=0))
        self.assertEqual(self.resolve(), self.price)

    def test_slot_range_is_strict(self):
        for slot in (-1, 8, True, "1", 1.0):
            with self.subTest(slot=slot):
                self.error("slot_out_of_range", lambda: self.table.add_value(self.price, slot=slot))

    def test_capacity_failure_preserves_existing_values(self):
        for slot in range(1, 8):
            self.table.add_value(self.price, slot=slot)
        self.error("table_full", lambda: self.table.add_value(self.price))
        self.assertEqual(self.resolve(), self.price)

    def test_type_role_and_unit_checked_independently(self):
        self.error("type_mismatch", lambda: self.resolve(expected_type=ValueType.DURATION))
        self.error("role_mismatch", lambda: self.resolve(expected_role="discount"))
        self.error("unit_mismatch", lambda: self.resolve(expected_unit="RIAL"))
        self.error("unit_mismatch", lambda: self.resolve(expected_unit=None))

    def test_same_type_different_role_rejected(self):
        other = self.table.add_value(ValueRecord(ValueType.PRICE, "999", "list_price", Origin.TOOL_RESULT, "TOMAN"))
        self.error("role_mismatch", lambda: self.resolve(other))

    def test_same_role_valid_choice_still_needs_semantic_scoring(self):
        other = self.table.add_value(ValueRecord(ValueType.PRICE, "999", "quoted_price", Origin.TOOL_RESULT, "TOMAN"))
        self.assertEqual(self.resolve(other).exact_text, "999")
        self.assertNotEqual(self.resolve(other).exact_text, self.price.exact_text)

    def test_cross_turn_same_slot_rejected(self):
        other = TurnReferences("quote-1")
        other_ref = other.add_value(self.price, slot=0)
        self.error("scope_mismatch", lambda: self.resolve(other_ref))

    def test_reset_reuse_does_not_revive_reference(self):
        self.table.reset()
        self.table.add_value(self.price, slot=0)
        self.error("expired_reference", lambda: self.resolve(self.ref))
        self.error("expired_reference", lambda: self.table.bind_selection("VAL_E0", scope_id=self.ref.scope_id, generation=self.ref.generation))

    def test_closed_turn_rejects_resolution_and_writes(self):
        self.table.close()
        self.error("closed_turn", lambda: self.resolve())
        self.error("closed_turn", lambda: self.table.add_value(self.price))
        self.error("closed_turn", self.table.reset)

    def test_resolved_records_cannot_be_mutated(self):
        with self.assertRaises(FrozenInstanceError):
            self.resolve().exact_text = "wrong"

    def test_no_hidden_gold_origin(self):
        self.error("invalid_record_type", lambda: ValueRecord(ValueType.PRICE, "100", "quoted_price", "gold_response"))

    def test_phone_leading_zeros_and_unicode_preserved(self):
        for exact in ("00982100123456", "۰۹۱۲۰۰۱۲۳۴۵"):
            record = ValueRecord(ValueType.PHONE, exact, "contact_phone", Origin.SEMANTIC_INPUT)
            ref = self.table.add_value(record)
            got = self.table.resolve_value(ref, expected_type=ValueType.PHONE, expected_role="contact_phone", expected_unit=None)
            self.assertEqual(got.exact_text, exact)

    def test_entity_name_pronunciation_and_role(self):
        entity = EntityRecord("product", "کالای آزمایشی X-۰۰۱", "quoted_item", Origin.TOOL_RESULT, "ایکس صفر صفر یک")
        ref = self.table.add_entity(entity, slot=15)
        got = self.table.resolve_entity(ref, expected_type="product", expected_role="quoted_item")
        self.assertEqual(got, entity)
        self.error("type_mismatch", lambda: self.table.resolve_entity(ref, expected_type="person", expected_role="quoted_item"))
        self.error("role_mismatch", lambda: self.table.resolve_entity(ref, expected_type="product", expected_role="seller"))
        self.error("kind_mismatch", lambda: self.resolve(ref))

    def test_reference_json_rejects_ambiguous_fields(self):
        for change, error in (({"slot": True}, "invalid_slot"), ({"generation": False}, "invalid_generation"), ({"scope_id": ""}, "invalid_scope")):
            self.error(error, lambda: Reference.from_dict({**self.ref.to_dict(), **change}))
        self.error("invalid_reference_fields", lambda: Reference.from_dict({**self.ref.to_dict(), "gold": "hidden"}))

    def test_records_reject_numeric_coercion(self):
        self.error("invalid_exact_text", lambda: ValueRecord(ValueType.PRICE, 12.5, "price", Origin.TOOL_RESULT))


if __name__ == "__main__":
    unittest.main()
