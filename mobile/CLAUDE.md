# mobile/ — RoadScan citizen app (WP4)

Flutter app for RoadScan (Pothole Detection & Management MVP, Tunisia). This is the
citizen-facing half of the product: photo capture, GPS/speed/direction reading, an
offline queue, and (later) a hands-free driving mode. No account/login — citizens
track their own reports via a locally generated `device_report_id`.

Owner: @JedBelhaj · Co-owner: @AymenJeddou. Full plan: `../docs/Sprint1_Action_Plan.md`
(Section 3 WP4 for tasks, Section 4.1 for the frozen data contract).

## Current scope (Sprint 3-4)

See `README.md` for the feature list: one-tap capture with undo and blur
check, persistent report store with retry/backoff, status sync with local
notifications, live clustered map with "I see it too" actions, and the
driving mode (server-side frame scoring, voice "pothole ahead" alerts).
All state goes through `SabeelData` (`services/sabeel_data.dart`); pure
rules live in `services/rules.dart` and are unit-tested.

## The frozen data contract (docs/Sprint1_Action_Plan.md §4.1)

Every report this app produces must serialize to **exactly** these field names — this is
frozen for Sprint 1, shared with WP3 (API) and WP1 (model). See `lib/models/report_draft.dart`.

```
device_report_id, lat, lon, gps_accuracy_m, speed_kmh, direction_deg, captured_at, source
```

Rules that matter:
- `lat` before `lon`, always — never `lng`, never swapped.
- `captured_at` is UTC ISO 8601 with a trailing `Z`, no fractional seconds
  (`lib/utils/iso8601.dart`, e.g. `2026-09-15T10:32:00Z`).
- `source` is `"manual"` or `"driving_mode"` (the web app sends `"web"`).
- `report_id`, `score`, `confidence`, `status` etc. are server-assigned (WP3/WP1) and
  don't exist on the phone yet — don't add them to `ReportDraft`.

## Design

`design/main.png`, `map.png`, `reports.png` define the 3-tab shape this app follows:
Accueil (home + camera CTA) / Carte (map) / Mes signalements (local reports list). Where
the mockups assume backend data that doesn't exist yet (city-wide stats, live map tiles,
the 4-step status tracker), the screens show an honest local/placeholder state instead of
fabricated numbers — see the doc comments at the top of each screen file for specifics.

## Layout

See the Layout section of `README.md`. State is threaded via constructors (no
`provider`/`riverpod`): `SabeelData` is built once in `main.dart` and passed
down; screens rebuild on it via `ListenableBuilder`.

## Verification

```
flutter pub get
flutter analyze
dart format --output=none --set-exit-if-changed lib test
flutter test
```

`flutter test` runs headless (no emulator/device). Actually running the app
(`flutter run`), on-device GPS/camera checks, and screenshots are done manually, not by CI
or an assistant.

## Git workflow

Branch off `dev`, PR into `dev` (never `main`), get a review from @AymenJeddou before
merging. Note: this repo's tracked main branch is `wp1-ai-model`, not `dev` — check which
branch actually exists before opening the PR.
