# mobile/ — RoadScan citizen app (WP4)

Flutter app for RoadScan (Pothole Detection & Management MVP, Tunisia). This is the
citizen-facing half of the product: photo capture, GPS/speed/direction reading, an
offline queue, and (later) a hands-free driving mode. No account/login — citizens
track their own reports via a locally generated `device_report_id`.

Owner: @JedBelhaj · Co-owner: @AymenJeddou. Full plan: `../docs/Sprint1_Action_Plan.md`
(Section 3 WP4 for tasks, Section 4.1 for the frozen data contract).

## Sprint 1 scope (deadline 2026-09-21)

Definition of done:
- App opens, captures a photo, and logs GPS/speed/direction correctly on a real device
- `device_report_id` generation implemented
- Offline queue data shape sketched (doc or code stub)

**Explicitly out of scope this sprint** — don't build these without checking the plan first:
- Hands-free driving mode (`home_screen.dart`'s "Mode conduite" is a stub that just shows a snackbar)
- Any backend/API calls — nothing is uploaded; values are only logged via `debugPrint`
- Full offline-queue sync/retry logic — only the data shape + local persistence exist

Since the dashboard work, the app talks to the Core API (`lib/services/api_client.dart`):
reports are uploaded with an anonymous persistent `device_id` (`services/device.dart`),
`SabeelData` (`services/sabeel_data.dart`) feeds the map (every pothole, coloured by
severity), "Mes Rapports" (this phone's reports + live status) and the home stats, and
retries the offline queue. `screens/support_chat_screen.dart` is the citizen side of the
dashboard's Messages inbox. Widget tests inject `test/helpers/offline_api.dart`.

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
- `source` is `"manual"` or `"driving_mode"` — only `"manual"` exists this sprint.
- `report_id`, `score`, `confidence`, `status` etc. are server-assigned (WP3/WP1) and
  don't exist on the phone yet — don't add them to `ReportDraft`.

## Design

`design/main.png`, `map.png`, `reports.png` define the 3-tab shape this app follows:
Accueil (home + camera CTA) / Carte (map) / Mes signalements (local reports list). Where
the mockups assume backend data that doesn't exist yet (city-wide stats, live map tiles,
the 4-step status tracker), the screens show an honest local/placeholder state instead of
fabricated numbers — see the doc comments at the top of each screen file for specifics.

## Layout

```
lib/
  main.dart                              # entry point: init SharedPreferences, load queue, run app
  app/roadscan_app.dart                  # MaterialApp + theme
  screens/root_shell.dart                # 3-tab NavigationBar shell
  screens/home_screen.dart               # Accueil
  screens/map_screen.dart                # Carte (placeholder body)
  screens/reports_screen.dart            # Mes signalements (reads the local queue)
  screens/camera_capture_screen.dart     # live camera preview + shutter
  screens/report_preview_screen.dart     # post-capture: GPS/speed/compass, confirm/retake
  models/report_draft.dart               # exact contract fields, toApiJson/fromApiJson
  models/queued_report.dart              # ReportDraft + local-only fields (offline queue shape)
  services/location_service.dart         # geolocator (GPS/speed) + flutter_compass (heading)
  services/offline_queue_repository.dart # ChangeNotifier, persisted via shared_preferences
  utils/iso8601.dart                     # contract-exact UTC ISO 8601 formatting
```

State is threaded via constructors (no `provider`/`riverpod`) — `OfflineQueueRepository` is
built once in `main.dart` and passed down; screens rebuild on it via `ListenableBuilder`.

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
