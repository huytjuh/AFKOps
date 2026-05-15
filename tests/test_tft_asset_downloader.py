from pathlib import Path

from tools.download_tft_set_assets import (
    asset_path_to_url,
    collect_asset_refs,
    is_set17_record,
    is_shop_champion_id,
)


def test_maps_lol_game_data_path_to_communitydragon_url() -> None:
    url = asset_path_to_url(
        "/lol-game-data/assets/ASSETS/UX/TFT/Champions/TFT17_Ahri.png",
        "pbe",
    )

    assert url == (
        "https://raw.communitydragon.org/pbe/"
        "plugins/rcp-be-lol-game-data/global/default/assets/ux/tft/champions/tft17_ahri.png"
    )


def test_filters_set17_records() -> None:
    assert is_set17_record({"set": "TFTSet17", "name": "Ahri"})
    assert not is_set17_record({"set": "TFTSet16", "name": "Ahri"})


def test_collects_asset_refs_from_record() -> None:
    refs = collect_asset_refs(
        "champions",
        [
            {
                "set": "TFTSet17",
                "apiName": "TFT17_Ahri",
                "display_name": "Ahri",
                "squareIconPath": "/lol-game-data/assets/ASSETS/UX/TFT/Champions/TFT17_Ahri.png",
            }
        ],
        "pbe",
        Path("assets/riot/tft/set17"),
    )

    assert len(refs) == 1
    assert refs[0].owner_id == "tft17_ahri"
    assert refs[0].category == "champions"


def test_shop_champion_filter_excludes_helper_units() -> None:
    assert is_shop_champion_id("tft17_ahri")
    assert not is_shop_champion_id("tft17_pve_minion")
    assert not is_shop_champion_id("tft17_darkstar_fakeunit")
