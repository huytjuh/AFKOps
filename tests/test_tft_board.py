from pathlib import Path

from afkops.bots.tft.board import BoardLayout, BoardMatrixBuilder
from afkops.core.vision import Detection


def detection(label: str, x: int, y: int, confidence: float = 1.0) -> Detection:
    return Detection(label=label, confidence=confidence, x=x - 10, y=y - 10, width=20, height=20)


def test_board_layout_loads_bench_and_field_slots() -> None:
    layout = BoardLayout.load(Path("assets/layouts/tft/board_1600x1000.toml"))

    assert len([slot for slot in layout.slots if slot.kind == "bench"]) == 9
    assert len([slot for slot in layout.slots if slot.kind == "field"]) == 28


def test_board_matrix_assigns_champion_to_nearest_slot() -> None:
    layout = BoardLayout.load(Path("assets/layouts/tft/board_1600x1000.toml"))

    matrix = BoardMatrixBuilder().build(
        layout,
        [
            detection("champion_ahri", 310, 714),
            detection("champion_teemo", 542, 394),
        ],
    )

    assert matrix.champion_at("bench_1") == "ahri"
    assert matrix.champion_at("field_2") == "teemo"
    assert matrix.as_dict()["bench_2"] is None


def test_board_matrix_builds_slot_occupancy_without_champion_identity() -> None:
    layout = BoardLayout.load(Path("assets/layouts/tft/board_1600x1000.toml"))

    matrix = BoardMatrixBuilder().build_occupancy(
        layout,
        [
            detection("bench_occupied", 310, 714),
            detection("field_unit", 542, 394),
        ],
    )

    assert matrix.is_occupied("bench_1")
    assert matrix.is_occupied("field_2")
    assert not matrix.is_occupied("bench_2")
    assert matrix.champion_at("bench_1") is None


def test_board_layout_scales_to_client_size() -> None:
    layout = BoardLayout.load(Path("assets/layouts/tft/board_1600x1000.toml"))

    scaled = layout.scaled(image_width=800, image_height=500)

    assert scaled.slots[0].center == (155, 359)


def test_board_layout_has_staggered_field_rows() -> None:
    layout = BoardLayout.load(Path("assets/layouts/tft/board_1600x1000.toml"))
    fields = [slot for slot in layout.slots if slot.kind == "field"]

    assert fields[0].center == (426, 396)
    assert fields[7].center == (481, 477)
    assert fields[14].center == (426, 556)
    assert fields[21].center == (481, 637)
