from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


CDRAGON_BASE = "https://raw.communitydragon.org/{version}/"
GAME_DATA_PREFIX = "/lol-game-data/assets/"
SET_PATTERN = re.compile(r"(tftset17|tft_set17|set17|tft17)", re.IGNORECASE)

JSON_SOURCES = {
    "champions": "plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json",
    "items": "plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json",
    "traits": "plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".dds"}
NON_SHOP_CHAMPION_TOKENS = {
    "animasquadprop",
    "darkstardamagetracker",
    "darkstar_fakeunit",
    "drxtracker",
    "enemy_",
    "ivernminion",
    "missfortune_traitclone",
    "primordiantracker",
    "pve_",
    "summon",
    "timebreakercore",
}


@dataclass(frozen=True)
class AssetRef:
    category: str
    owner_id: str
    owner_name: str
    source_field: str
    source_path: str
    url: str
    output_path: str


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def is_set17_record(record: dict[str, Any]) -> bool:
    values = [
        str(record.get("set", "")),
        str(record.get("apiName", "")),
        str(record.get("characterName", "")),
        str(record.get("character_name", "")),
        str(record.get("name", "")),
        str(record.get("display_name", "")),
        str(record.get("trait_id", "")),
        json.dumps(record.get("sets", ""), ensure_ascii=False),
    ]
    return any(SET_PATTERN.search(value) for value in values)


def iter_asset_paths(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            paths.extend(iter_asset_paths(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(iter_asset_paths(child, f"{prefix}[{index}]"))
    elif isinstance(value, str) and looks_like_asset_path(value):
        paths.append((prefix, value))
    return paths


def looks_like_asset_path(value: str) -> bool:
    lower = value.lower()
    return (
        lower.startswith(GAME_DATA_PREFIX)
        or lower.startswith("assets/")
        or lower.startswith("/assets/")
        or lower.startswith("game/assets/")
    ) and Path(lower).suffix in IMAGE_EXTENSIONS


def asset_path_to_url(path: str, version: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith(GAME_DATA_PREFIX):
        relative = normalized.removeprefix(GAME_DATA_PREFIX)
        return CDRAGON_BASE.format(version=version) + (
            "plugins/rcp-be-lol-game-data/global/default/" + quote(relative.lower())
        )
    if normalized.startswith("/assets/"):
        normalized = normalized[1:]
    if normalized.startswith("assets/"):
        return CDRAGON_BASE.format(version=version) + (
            "plugins/rcp-be-lol-game-data/global/default/" + quote(normalized.lower())
        )
    return CDRAGON_BASE.format(version=version) + quote(normalized.lower())


def record_id(record: dict[str, Any], fallback: str) -> str:
    for key in ["apiName", "characterName", "character_name", "trait_id", "name", "display_name"]:
        value = record.get(key)
        if value:
            return slugify(str(value))
    return fallback


def record_name(record: dict[str, Any], fallback: str) -> str:
    for key in ["display_name", "name", "apiName", "characterName"]:
        value = record.get(key)
        if value:
            return str(value)
    return fallback


def collect_asset_refs(
    category: str,
    records: list[dict[str, Any]],
    version: str,
    output_root: Path,
) -> list[AssetRef]:
    refs: list[AssetRef] = []
    for index, record in enumerate(records):
        if not is_set17_record(record):
            continue

        owner_id = record_id(record, f"{category}_{index}")
        owner_name = record_name(record, owner_id)
        for source_field, source_path in iter_asset_paths(record):
            url = asset_path_to_url(source_path, version)
            suffix = Path(source_path).suffix.lower()
            filename = f"{owner_id}__{slugify(source_field)}{suffix}"
            refs.append(
                AssetRef(
                    category=category,
                    owner_id=owner_id,
                    owner_name=owner_name,
                    source_field=source_field,
                    source_path=source_path,
                    url=url,
                    output_path=str(output_root / category / filename),
                )
            )
    return dedupe_refs(refs)


def dedupe_refs(refs: list[AssetRef]) -> list[AssetRef]:
    seen: set[tuple[str, str]] = set()
    unique: list[AssetRef] = []
    for ref in refs:
        key = (ref.url, ref.output_path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(ref)
    return unique


def download_json(source: str, version: str) -> list[dict[str, Any]]:
    url = CDRAGON_BASE.format(version=version) + source
    with urlopen(request(url)) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(request(url)) as response:
            output_path.write_bytes(response.read())
        return True
    except (HTTPError, URLError) as exc:
        print(f"[warn] failed {url}: {exc}")
        return False


def request(url: str) -> Request:
    return Request(
        url,
        headers={
            "User-Agent": "AFKOps asset downloader (Python urllib)",
            "Accept": "application/json,image/*,*/*",
        },
    )


def write_manifest(output_root: Path, refs: list[AssetRef]) -> None:
    manifest_path = output_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps([asdict(ref) for ref in refs], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def copy_champion_templates(refs: list[AssetRef], templates_dir: Path) -> None:
    templates_dir.mkdir(parents=True, exist_ok=True)
    for ref in refs:
        if ref.category != "champions":
            continue
        if not is_shop_champion_id(ref.owner_id):
            continue
        if "square" not in ref.source_path.lower() and "icon" not in ref.source_field.lower():
            continue

        source = Path(ref.output_path)
        if not source.exists() or source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        shutil.copy2(source, templates_dir / f"{ref.owner_id}{source.suffix.lower()}")


def is_shop_champion_id(owner_id: str) -> bool:
    normalized = owner_id.lower()
    return not any(token in normalized for token in NON_SHOP_CHAMPION_TOKENS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download TFT Set 17 ML assets from CommunityDragon.")
    parser.add_argument("--version", default="pbe", help="CommunityDragon version, for example pbe/latest.")
    parser.add_argument("--output-dir", type=Path, default=Path("assets/riot/tft/set17"))
    parser.add_argument("--dry-run", action="store_true", help="Collect and print refs without files.")
    parser.add_argument("--limit", type=int, help="Download only the first N assets for a smoke test.")
    parser.add_argument(
        "--copy-champion-templates",
        action="store_true",
        help="Copy downloaded champion shop portraits into assets/templates/tft/champions.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_refs: list[AssetRef] = []

    for category, source in JSON_SOURCES.items():
        print(f"Reading {category}: {source}")
        records = download_json(source, args.version)
        refs = collect_asset_refs(category, records, args.version, args.output_dir)
        print(f"  set17 records/assets: {len(refs)}")
        all_refs.extend(refs)

    write_manifest(args.output_dir, all_refs)
    refs_to_download = all_refs[: args.limit] if args.limit else all_refs

    for ref in refs_to_download:
        print(f"{ref.category:<10} {ref.owner_id:<32} {ref.source_field}")
        if not args.dry_run:
            download_file(ref.url, Path(ref.output_path))

    if args.copy_champion_templates and not args.dry_run:
        copy_champion_templates(all_refs, Path("assets/templates/tft/champions"))

    print(f"Manifest: {args.output_dir / 'manifest.json'}")
    print(f"Assets selected: {len(all_refs)}")
    print(f"Assets downloaded: {0 if args.dry_run else len(refs_to_download)}")


if __name__ == "__main__":
    main()
