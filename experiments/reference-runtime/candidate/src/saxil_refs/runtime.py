"""Preserve exact text outside a model, with explicit scope/type/role checks.

The model chooses an alias. The host owns the table, scope and expected role.
This module does not generate semantic decisions or authenticate remote peers.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ReferenceError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Origin(str, Enum):
    SEMANTIC_INPUT = "semantic_input"
    SESSION_STATE = "session_state"
    TOOL_RESULT = "tool_result"


class ValueType(str, Enum):
    PRICE = "PRICE"
    INTEGER = "INTEGER"
    DURATION = "DURATION"
    DATE = "DATE"
    TIME = "TIME"
    PHONE = "PHONE"
    PERCENTAGE = "PERCENTAGE"


def _text(value, code: str, *, optional: bool = False):
    if optional and value is None:
        return
    if not isinstance(value, str) or not value:
        raise ReferenceError(code)


@dataclass(frozen=True)
class ValueRecord:
    value_type: ValueType
    exact_text: str
    role: str
    origin: Origin
    unit: str | None = None

    def __post_init__(self):
        if not isinstance(self.value_type, ValueType) or not isinstance(self.origin, Origin):
            raise ReferenceError("invalid_record_type")
        _text(self.exact_text, "invalid_exact_text")
        _text(self.role, "invalid_role")
        _text(self.unit, "invalid_unit", optional=True)


@dataclass(frozen=True)
class EntityRecord:
    entity_type: str
    exact_name: str
    role: str
    origin: Origin
    pronunciation: str | None = None

    def __post_init__(self):
        if not isinstance(self.origin, Origin):
            raise ReferenceError("invalid_origin")
        _text(self.entity_type, "invalid_entity_type")
        _text(self.exact_name, "invalid_exact_name")
        _text(self.role, "invalid_role")
        _text(self.pronunciation, "invalid_pronunciation", optional=True)


@dataclass(frozen=True)
class Reference:
    scope_id: str
    generation: int
    kind: str
    slot: int

    def __post_init__(self):
        if not isinstance(self.scope_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.scope_id):
            raise ReferenceError("invalid_scope")
        if type(self.generation) is not int or self.generation < 0:
            raise ReferenceError("invalid_generation")
        if not isinstance(self.kind, str) or self.kind not in ("value", "entity"):
            raise ReferenceError("invalid_kind")
        if type(self.slot) is not int or self.slot < 0:
            raise ReferenceError("invalid_slot")

    @property
    def alias(self) -> str:
        return ("VAL_E" if self.kind == "value" else "ENT_E") + str(self.slot)

    def to_dict(self) -> dict:
        return {"scope_id": self.scope_id, "generation": self.generation, "kind": self.kind, "slot": self.slot}

    @classmethod
    def from_dict(cls, payload: Mapping) -> Reference:
        if not isinstance(payload, Mapping) or set(payload) != {"scope_id", "generation", "kind", "slot"}:
            raise ReferenceError("invalid_reference_fields")
        return cls(**payload)


class TurnReferences:
    """One host-owned turn table. Reset invalidates all issued references.

    Keep this object outside model-controlled data. It is not thread-safe.
    References are correlation metadata, not authorization credentials.
    """

    def __init__(self, turn_id: str, *, value_capacity: int = 8, entity_capacity: int = 16):
        _text(turn_id, "invalid_turn")
        for capacity, maximum in ((value_capacity, 8), (entity_capacity, 16)):
            if type(capacity) is not int or not 1 <= capacity <= maximum:
                raise ReferenceError("invalid_capacity")
        self.turn_id = turn_id
        self._scope_id = secrets.token_hex(16)
        self._generation = 0
        self._capacities = {"value": value_capacity, "entity": entity_capacity}
        self._values: dict[int, ValueRecord] = {}
        self._entities: dict[int, EntityRecord] = {}
        self._closed = False

    @property
    def scope_id(self):
        return self._scope_id

    @property
    def generation(self):
        return self._generation

    def _open(self):
        if self._closed:
            raise ReferenceError("closed_turn")

    def _table(self, kind):
        return self._values if kind == "value" else self._entities

    def _add(self, kind, record, slot):
        self._open()
        table = self._table(kind)
        capacity = self._capacities[kind]
        if slot is None:
            slot = next((candidate for candidate in range(capacity) if candidate not in table), None)
            if slot is None:
                raise ReferenceError("table_full")
        if type(slot) is not int or not 0 <= slot < capacity:
            raise ReferenceError("slot_out_of_range")
        if slot in table:
            raise ReferenceError("duplicate_slot")
        table[slot] = record
        return Reference(self.scope_id, self.generation, kind, slot)

    def add_value(self, record: ValueRecord, *, slot: int | None = None) -> Reference:
        if not isinstance(record, ValueRecord):
            raise ReferenceError("invalid_value_record")
        return self._add("value", record, slot)

    def add_entity(self, record: EntityRecord, *, slot: int | None = None) -> Reference:
        if not isinstance(record, EntityRecord):
            raise ReferenceError("invalid_entity_record")
        return self._add("entity", record, slot)

    def _get(self, reference: Reference, kind: str):
        self._open()
        if not isinstance(reference, Reference):
            raise ReferenceError("invalid_reference")
        if reference.scope_id != self.scope_id:
            raise ReferenceError("scope_mismatch")
        if reference.generation != self.generation:
            raise ReferenceError("expired_reference")
        if reference.kind != kind:
            raise ReferenceError("kind_mismatch")
        if reference.slot not in self._table(kind):
            raise ReferenceError("unknown_reference")
        return self._table(kind)[reference.slot]

    def resolve_value(self, reference: Reference, *, expected_type: ValueType, expected_role: str, expected_unit: str | None) -> ValueRecord:
        if not isinstance(expected_type, ValueType):
            raise ReferenceError("invalid_expected_type")
        _text(expected_role, "invalid_expected_role")
        _text(expected_unit, "invalid_expected_unit", optional=True)
        record = self._get(reference, "value")
        if record.value_type != expected_type:
            raise ReferenceError("type_mismatch")
        if record.role != expected_role:
            raise ReferenceError("role_mismatch")
        if record.unit != expected_unit:
            raise ReferenceError("unit_mismatch")
        return record

    def resolve_entity(self, reference: Reference, *, expected_type: str, expected_role: str) -> EntityRecord:
        _text(expected_type, "invalid_expected_type")
        _text(expected_role, "invalid_expected_role")
        record = self._get(reference, "entity")
        if record.entity_type != expected_type:
            raise ReferenceError("type_mismatch")
        if record.role != expected_role:
            raise ReferenceError("role_mismatch")
        return record

    def bind_selection(self, alias: str, *, scope_id: str, generation: int) -> Reference:
        """Bind a model alias to the host's original request envelope.

        The host must retain that envelope from request dispatch. Reading the
        current scope at response arrival would lose stale-response protection.
        """
        self._open()
        if scope_id != self.scope_id:
            raise ReferenceError("scope_mismatch")
        if type(generation) is not int or generation != self.generation:
            raise ReferenceError("expired_reference")
        match = re.fullmatch(r"(VAL|ENT)_E(0|[1-9][0-9]*)", alias) if isinstance(alias, str) and len(alias) <= 16 else None
        if match is None:
            raise ReferenceError("invalid_alias")
        kind = "value" if match.group(1) == "VAL" else "entity"
        reference = Reference(scope_id, generation, kind, int(match.group(2)))
        self._get(reference, kind)
        return reference

    def reset(self):
        self._open()
        self._generation += 1
        self._values.clear()
        self._entities.clear()

    def close(self):
        self._values.clear()
        self._entities.clear()
        self._closed = True
