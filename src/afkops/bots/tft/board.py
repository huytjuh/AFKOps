from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from pathlib import Path
import tomllib

from afkops.core.vision import Detection


@dataclass(frozen=True)
class BoardSlot:
    id: str
    kind: str
    x: int
    y: int

    @property
    def center(self) -> tuple[int, int]:
        return self.x, self.y


@dataclass(frozen=True)
class BoardLayout:
    reference_width: int
    reference_height: int
    assignment_radius: int
    slots: tuple[BoardSlot, ...]

    @classmethod
    def load(cls, path: Path) -> "BoardLayout":
        with path.open("rb") as file:
            data = tomllib.load(file)

        slots = tuple(
            BoardSlot(
                id=slot["id"],
                kind=slot["kind"],
                x=int(slot["x"]),
                y=int(slot["y"]),
            )
            for slot in data["slots"]
        )
        return cls(
            reference_width=int(data["reference_width"]),
            reference_height=int(data["reference_height"]),
            assignment_radius=int(data["assignment_radius"]),
            slots=slots,
        )

    def scaled(self, image_width: int, image_height: int) -> "BoardLayout":
        scale_x = image_width / self.reference_width
        scale_y = image_height / self.reference_height
        return BoardLayout(
            reference_width=image_width,
            reference_height=image_height,
            assignment_radius=round(self.assignment_radius * ((scale_x + scale_y) / 2)),
            slots=tuple(
                BoardSlot(
                    id=slot.id,
                    kind=slot.kind,
                    x=round(slot.x * scale_x),
                    y=round(slot.y * scale_y),
                )
                for slot in self.slots
            ),
        )


@dataclass(frozen=True)
class ChampionAssignment:
    slot_id: str
    champion: str
    confidence: float


class BoardMatrix:
    def __init__(
        self,
        slot_ids: list[str] | None = None,
        assignments: dict[str, ChampionAssignment] | None = None,
        occupied_slots: set[str] | None = None,
    ) -> None:
        self.slot_ids = slot_ids or []
        self.assignments = assignments or {}
        self.occupied_slots = occupied_slots or set(self.assignments)

    def champion_at(self, slot_id: str) -> str | None:
        assignment = self.assignments.get(slot_id)
        return assignment.champion if assignment else None

    def is_occupied(self, slot_id: str) -> bool:
        return slot_id in self.occupied_slots or slot_id in self.assignments

    def open_slots(self, kind: str | None = None) -> list[str]:
        slot_ids = self.slot_ids
        if kind:
            prefix = f"{kind}_"
            slot_ids = [slot_id for slot_id in slot_ids if slot_id.startswith(prefix)]
        return [slot_id for slot_id in slot_ids if not self.is_occupied(slot_id)]

    def occupied_count(self, kind: str | None = None) -> int:
        slot_ids = self.slot_ids
        if kind:
            prefix = f"{kind}_"
            slot_ids = [slot_id for slot_id in slot_ids if slot_id.startswith(prefix)]
        return sum(1 for slot_id in slot_ids if self.is_occupied(slot_id))

    def as_dict(self) -> dict[str, str | None]:
        return {
            slot_id: self.assignments[slot_id].champion if slot_id in self.assignments else None
            for slot_id in self.slot_ids
        }

    def occupancy_dict(self) -> dict[str, bool]:
        return {slot_id: self.is_occupied(slot_id) for slot_id in self.slot_ids}


class BoardMatrixBuilder:
    champion_prefix = "champion_"
    occupancy_labels = {
        "bench_occupied",
        "field_occupied",
        "slot_occupied",
        "unit_occupied",
        "board_unit",
        "bench_unit",
        "field_unit",
    }

    def build(self, layout: BoardLayout, detections: list[Detection]) -> BoardMatrix:
        assignments: dict[str, ChampionAssignment] = {}
        champion_detections = [
            detection
            for detection in detections
            if detection.label.startswith(self.champion_prefix)
        ]

        for detection in champion_detections:
            slot = self._nearest_slot(layout, detection.center)
            if slot is None:
                continue

            champion = detection.label.removeprefix(self.champion_prefix)
            existing = assignments.get(slot.id)
            if existing is None or detection.confidence > existing.confidence:
                assignments[slot.id] = ChampionAssignment(
                    slot_id=slot.id,
                    champion=champion,
                    confidence=detection.confidence,
                )

        return BoardMatrix(slot_ids=[slot.id for slot in layout.slots], assignments=assignments)

    def build_occupancy(self, layout: BoardLayout, detections: list[Detection]) -> BoardMatrix:
        occupied_slots: set[str] = set()
        occupancy_detections = [
            detection
            for detection in detections
            if detection.label in self.occupancy_labels
            or detection.label.startswith(("occupied_", "unit_on_"))
        ]

        for detection in occupancy_detections:
            slot = self._nearest_slot(layout, detection.center)
            if slot is None:
                continue
            occupied_slots.add(slot.id)

        return BoardMatrix(slot_ids=[slot.id for slot in layout.slots], occupied_slots=occupied_slots)

    def _nearest_slot(self, layout: BoardLayout, point: tuple[int, int]) -> BoardSlot | None:
        nearest_slot: BoardSlot | None = None
        nearest_distance = float("inf")
        for slot in layout.slots:
            distance = hypot(slot.x - point[0], slot.y - point[1])
            if distance < nearest_distance:
                nearest_slot = slot
                nearest_distance = distance

        if nearest_slot is None or nearest_distance > layout.assignment_radius:
            return None
        return nearest_slot
