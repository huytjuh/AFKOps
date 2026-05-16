# AFKOps

AFKOps is a Python automation framework for computer-vision bots. The shared core handles screen capture, object/template detection, and mouse input, while each bot owns its own game state, target priorities, and actions.

The first concrete target is the TFT bot. Hearthstone, Slay the Spire, and Twitch playback monitoring are scaffolded for later work.

## Project Structure

```text
AFKOps/
├── apps/
│   └── tft_app.py
├── assets/
│   └── tft/
│       ├── league_client/
│       ├── teamfight_tactics_ui/
│       └── game_assets/
├── configs/
│   └── tft.example.toml
├── data/
│   ├── labels/
│   └── screenshots/
├── models/
├── src/
│   └── afkops/
│       ├── cli.py
│       ├── core/
│       │   ├── config.py
│       │   ├── input.py
│       │   ├── screen.py
│       │   └── vision.py
│       └── bots/
│           ├── tft/
│           │   └── bot.py
│           ├── hearthstone/
│           │   └── bot.py
│           ├── slay_the_spire/
│           │   └── bot.py
│           └── twitch_viewer/
│               └── bot.py
└── tests/
    └── test_tft_bot.py
```

## Bot Layout

- `src/afkops/core/screen.py`: captures the screen with `mss`.
- `src/afkops/core/vision.py`: shared OpenCV detection primitives.
- `src/afkops/core/input.py`: mouse interaction with dry-run protection.
- `src/afkops/bots/tft/bot.py`: small orchestrator for the four TFT modules.
- `assets/tft/`: TFT-specific client templates, in-game UI templates, and set assets.
- `models/`: future object detection weights, such as YOLO exports.
- `data/tft/screenshots/`: local TFT screenshots for labeling/training.
- `data/labels/`: annotations for object detection training.

## TFT Bot Start

Run the TFT bot as an app:

```powershell
python apps/tft_app.py
```

By default the app captures only this window:

```text
League of Legends (TM) Client
```

You can override it:

```powershell
python apps/tft_app.py --window-title "League of Legends"
```

The app runs in `dry_run` mode by default, so it prints intended clicks instead of moving the
mouse. Change `dry_run=True` to `dry_run=False` in `apps/tft_app.py` only after your detections
are reliable.

Before matchmaking, `TftClientLauncher.prepare_for_matchmaking(credentials)` checks for an open
League/TFT client. If none is found, it starts `riot_client_path`, waits for the login window,
scans for login text such as `username` or `password` when OCR is available, enters the Riot
credentials, and waits for the client to become ready. Without OCR it falls back to
`riot_login_form_delay_seconds`.

Credentials are loaded from `configs/tft_credentials.local.toml` by default, with `TFT_USERNAME`
and `TFT_PASSWORD` as a fallback. The local credentials file is git-ignored; use
`configs/tft_credentials.example.toml` as the tracked template.

Capture a screenshot for templates or training data:

```powershell
python apps/capture_tft_screen.py
```

The capture script also targets `League of Legends (TM) Client` by default. Use `--full-screen`
only when you intentionally want the whole monitor.

Screenshots are saved to:

```text
data/tft/screenshots/
```

Crop a template from a saved screenshot:

```powershell
python apps/crop_tft_template.py data/tft/screenshots/tft_YYYYMMDD_HHMMSS.png round_2_1
```

The cropper opens an OpenCV selection window. Drag the area, then press Enter or Space. You can
also crop with exact coordinates:

```powershell
python apps/crop_tft_template.py data/tft/screenshots/example.png round_2_1 --x 900 --y 20 --width 80 --height 30
```

Templates are saved to:

```text
assets/tft/teamfight_tactics_ui/
```

Evaluate saved templates against a screenshot:

```powershell
python apps/evaluate_tft_templates.py data/tft/screenshots/example.png --threshold 0.75
```

Example output:

```text
round_2_1                    0.942 at (901, 22)
find_match_button            0.883 at (720, 610)
```

Each TFT app loop writes a detection overlay to:

```text
data/tft/debug/latest_detection.png
```

Detected boxes are blue/orange. The selected click target is green.

Add button templates here:

```text
assets/tft/league_client/play_button.png
assets/tft/league_client/accept_button.png
assets/tft/league_client/find_match_button.png
assets/tft/league_client/confirm_button.png
assets/tft/league_client/play_again_button.png
assets/tft/teamfight_tactics_ui/buy_xp_button.png
assets/tft/teamfight_tactics_ui/reroll_button.png
assets/tft/teamfight_tactics_ui/champion_shop_slot_1.png
assets/tft/teamfight_tactics_ui/champion_shop_slot_2.png
assets/tft/teamfight_tactics_ui/champion_shop_slot_3.png
assets/tft/teamfight_tactics_ui/champion_shop_slot_4.png
assets/tft/teamfight_tactics_ui/champion_shop_slot_5.png
assets/tft/teamfight_tactics_ui/augment_choice_1.png
assets/tft/teamfight_tactics_ui/augment_choice_2.png
assets/tft/teamfight_tactics_ui/augment_choice_3.png
assets/tft/teamfight_tactics_ui/carousel_unit.png
assets/tft/teamfight_tactics_ui/carousel_marker.png
assets/tft/teamfight_tactics_ui/combat_marker.png
assets/tft/teamfight_tactics_ui/enemy_board_marker.png
```

## TFT States

The TFT bot is organized around four concise modules:

- `client_launcher.py`: starts the local game client when a client path and credentials are provided.
- `matchmaking.py`: opens the TFT play flow, starts matchmaking, and accepts ready checks.
- `gameplay.py`: plays the match through the configured TFT strategy.
- `requeue.py`: clicks play again so matchmaking can restart.

The TFT state resolver still splits live screen state into two top-level states:

- `league_client`: handles the League of Legends client flow and clicks queue/match buttons.
- `game_client`: handles the actual TFT game window.

The game client currently has four sub-states:

- `carousel`: pick a unit/item from the carousel.
- `planning`: buy units, reroll, buy XP, and later position units.
- `combat`: wait, scout, or collect combat information.
- `augment`: choose an augment.

## TFT Round Administration

The TFT round monitor uses this schedule:

```text
Stage 1:
1-1 portal_select/carousel
1-2 pve
1-3 pve
1-4 pve

Stages 2-7:
X-1 pvp
X-2 pvp
X-3 pvp
X-4 carousel
X-5 pvp
X-6 pvp
X-7 pve
```

Augment rounds are tracked as overlays on top of the normal round:

```text
2-1 silver augment
3-2 gold augment
4-2 prismatic augment
```

Each round has a round type, expected sub-state, optional augment tier, and description. Visual
detection still decides what is actually on screen, while the progression monitor keeps the
strategy synced to the stage/round schedule when it sees round labels such as `round_3_2`.

## TFT Strategy

Strategy options live in:

```text
configs/tft_strategy.example.toml
```

Copy it to `configs/tft_strategy.local.toml` for local tuning. The local file is ignored by git.

The TFT strategy now returns action objects instead of raw detections:

```text
wait
queue_match
accept_match
pick_augment
pick_carousel_unit
buy_unit
buy_xp
reroll
```

The bot keeps a small memory object for current round, detected state, last action, and future
values like gold, level, health, streak, and bench slots.

The basic TFT strategy engine uses these conservative rules:

```text
league client -> accept, confirm, queue, or open play flow
augment round -> pick augment by configured slot order
carousel round -> pick detected carousel unit
pve round -> collect loot, buy useful shop slot, or wait
pvp round -> buy identified preferred shop unit during planning signals, otherwise wait
combat -> wait
```

## TFT Shop Recognition

Plain `champion_shop_slot_1` through `champion_shop_slot_5` detections only mean the shop is
visible. The bot creates separate `buy_shop_slot_1` through `buy_shop_slot_5` detections when a
shop slot is identified as one of the configured `preferred_units`.

Shop identity can come from either signal:

```text
shop_champion_tft17_aatrox  # portrait/object model result
champion_tft17_aatrox       # template portrait result
shop_text_tft17_aatrox      # OCR/text model result
ocr_champion_tft17_aatrox   # OCR/text model result
```

When portrait and text agree, the buy confidence is boosted. When they disagree, the text result
wins because the name text under the portrait is usually the most direct shop identity signal.
The buy signal must also clear `shop_buy_confidence` from `configs/tft_strategy.local.toml`.

If this file exists, the TFT bot loads it with the optional `ultralytics` dependency and adds its
detections before shop recognition:

```text
models/tft/shop_detector.pt
```

Recommended model classes for the shop detector:

```text
shop_champion_tft17_aatrox
shop_text_tft17_aatrox
shop_champion_tft17_akali
shop_text_tft17_akali
```

## TFT Board Matrix

The board and bench coordinate asset lives here:

```text
assets/tft/teamfight_tactics_ui/board_1600x1000.toml
```

It defines 9 bench slots and 28 field hex slots using coordinates from a 1600x1000 League client
capture. The layout scales to the current captured client size.

Champion templates can be placed here:

```text
assets/tft/game_assets/champions/ahri.png
assets/tft/game_assets/champions/teemo.png
```

Those templates are detected as labels like:

```text
champion_ahri
champion_teemo
```

During planning state, champion detections are assigned to the nearest board slot and stored as a
matrix:

```text
bench_1 = ahri
bench_2 = teemo
field_1 = ahri
field_2 = teemo
```

The debug overlay draws the bench and field slot centers as pink markers so the coordinates can be
tuned from `data/tft/debug/latest_detection.png`.

For live planning decisions, the bot currently uses occupancy-only board detection. Model classes
such as these mark the nearest bench or field slot as occupied without trying to identify the
champion:

```text
bench_occupied
field_occupied
slot_occupied
board_unit
bench_unit
field_unit
```

If all nine bench slots are occupied, the strategy skips shop buying even when a preferred unit is
detected.

## TFT YOLO Vision

TFT has one shared lightweight YOLO detector for launcher and gameplay signals:

```text
models/tft/tft_fast_yolo.pt
```

The default base model is `yolo11n.pt`, with `imgsz=640` and a lower default confidence threshold
for speed and recall. If the model file is missing or Ultralytics is not installed, detection
returns no results and the bot falls back to templates/OCR where available.

Dataset folders live under:

```text
data/tft/yolo/images/train/
data/tft/yolo/images/val/
data/tft/yolo/labels/train/
data/tft/yolo/labels/val/
```

The dataset class map is in:

```text
configs/tft_yolo_dataset.yaml
```

Initial classes cover launcher controls, login text/fields, matchmaking controls, shop slots,
champion/text detections, board units, and core gameplay controls. Train with:

```powershell
python tools/train_tft_yolo.py --epochs 50 --imgsz 640
```

After training, copy the best weights to:

```text
models/tft/tft_fast_yolo.pt
```

## TFT Set Assets

Download Set 17 ML assets from CommunityDragon:

```powershell
python tools/download_tft_set_assets.py --copy-champion-templates
```

The downloader reads:

```text
tftchampions.json
tftitems.json
tfttraits.json
```

Downloaded assets and a manifest are saved to:

```text
assets/tft/game_assets/
```

Champion shop portraits are copied into:

```text
assets/tft/game_assets/champions/
```

The bot ignores helper/PvE/fake-unit champion portraits such as `pve_minion`, trackers, summons,
and fake units when loading champion templates.

Safety controls are enabled before real clicks:

```text
click_cooldown_seconds
max_clicks_per_minute
dry_run
```

Run the TFT bot in dry-run mode:

```powershell
afkops run tft
```

Run with real clicks only after the templates are reliable:

```powershell
afkops run tft --no-dry-run
```

## Detection Plan

Start with OpenCV template matching for simple clickable UI buttons. Move a bot to object detection when the same button appears in many sizes, themes, resolutions, or visual states.

Recommended order:

1. TFT bot with template matching.
2. Add screenshot capture helpers for collecting training data.
3. Add Hearthstone and Slay the Spire state machines.
4. Add object detection model loading behind the same `Detection` interface.
5. Keep Twitch automation limited to legitimate playback QA and stream health monitoring.
