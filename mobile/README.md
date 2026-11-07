# Sabeel mobile app (Flutter)

The citizen and driver app. No account: a random per-install `device_id`
ties a phone to its reports and its support chat.

## What it does

| Feature | How |
|---|---|
| **One-tap report** (#33) | "Signaler" opens the camera at once; GPS and compass start with it, so the shutter uses a fix under 10 s old. Framing guide and rotating tips. A non-blocking blur check (Laplacian variance in an isolate) offers "Reprendre" / "Garder". Then "Envoyé dans 5 s · Annuler": nothing is uploaded during the undo window. |
| **Detailed mode** | The Sprint 1 preview (GPS accuracy, speed, compass) before sending, from "Mode détaillé" on the home screen. |
| **Reliable upload** (#31) | Every report is stored on the phone first, with its upload state. Retries back off 30 s, 2 min, 10 min, then hourly; they run on app start, when the network returns (`connectivity_plus`) and every 30 s while the app is open. `POST /reports` is idempotent on `device_report_id`, so a retry can never create a duplicate. A report refused for good (4xx) stops retrying and shows why. |
| **No pothole detected** | If the model sees nothing, the report waits for the citizen's choice: "Reprendre" (drop it) or "Envoyer quand même" (resend with `force=true`; an officer checks it). |
| **History and tracker** (#31) | "Mes Rapports" lists every report (uploaded or not) with the 4-step tracker Reçu → Confirmé → Transmis → Réparé, synced from `GET /devices/{id}/reports`. |
| **Notifications** | A local notification when a report becomes confirmed, sent, fixed or reopened. The permission is asked after the first report, not at launch. |
| **Live map** (#32) | `GET /map` for the visible area, reloaded 400 ms after the map stops moving; grid clustering keeps 5,000+ points smooth; filters Ouverts / Urgents / Réparés; the last result stays visible offline ("données hors ligne"); your own potholes have a navy ring. |
| **"I see it too"** (#32) | On a pothole card: "Je le vois aussi", or "Toujours là" / "Bien réparé" on a fixed one, and "Pas un nid-de-poule". Enabled only within 50 m with GPS better than 40 m (same rule as the server); the server's 403 / 409 / 429 answers are shown in plain French. |
| **Driving mode** (F6) | Phone on the windscreen. Every 1.5 s between 5 and 80 km/h, a 640 px frame is scored by `POST /detect` (the server stores nothing). Three positive frames in a row upload a `driving_mode` report. Known potholes of severity ≥ 3 within 200 m ahead (±30° of the heading) are announced by voice ("Attention, nid-de-poule dans 150 mètres", `flutter_tts`) and vibration. The screen stays on (`wakelock_plus`). |
| **Support chat** | Messages to the authorities' inbox. |

Decision OP-1 (cahier 19.5): driving-mode detection runs **on the server**,
not on the phone. It reuses the exact production model with no second export
to maintain; the cost is about 40 KB of upload per frame.

## Run

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000     # Android emulator
flutter run --dart-define=API_BASE_URL=http://<PC LAN IP>:8000  # phone on the same Wi-Fi
# phone over USB: adb reverse tcp:8000 tcp:8000 and API_BASE_URL=http://127.0.0.1:8000
```

The release APK is built by CI (`.github/workflows/mobile-apk.yml`) and
attached to each GitHub release; point it at the deployed API with
`--dart-define=API_BASE_URL=https://...`.

## Check

```bash
flutter analyze
dart format --output=none --set-exit-if-changed lib test
flutter test
```

Tests cover the backoff schedule, the upload/retry/idempotency flow, the
not-detected decision, status sync, the Sprint 1 queue migration, the status
diff that drives notifications, the geofence, "pothole ahead", the speed gate,
the 3-frame rule, map clustering (5,000 points), the blur metric and the
sensor freshness rule.

## Field checks still to do on a real phone

- **< 15 s report target** (#33): debug builds log the timings (camera ready,
  shutter, queued, server ack) as `capture timings`. Record the median of 10
  real attempts.
- **Blur threshold**: `blurThreshold = 100` in `lib/services/rules.dart` is
  the usual OpenCV starting value; calibrate it on 10 real photos (5 sharp,
  5 blurred).
- **Driving mode**: a 20-minute drive for heat and battery, and the
  frame interval (1.5 s).

## Layout

```
lib/
  main.dart                    store, device id, notifications, connectivity, 30 s refresh
  services/sabeel_data.dart    upload with backoff, status sync + notifications, map cache
  services/offline_queue_repository.dart   persistent report store
  services/api_client.dart     every Core API call
  services/rules.dart          pure rules (backoff, diff, geofence, ahead, clustering, blur)
  services/live_sensors.dart   GPS + compass stream while the camera is open
  services/photo_tools.dart    photo storage, blur score, frame downscale (isolates)
  services/notifier.dart       local notifications
  screens/camera_capture_screen.dart   quick, detailed and driving modes
  screens/map_screen.dart      live map, clustering, pothole card and confirmations
  screens/reports_screen.dart  history, upload state, tracker
  widgets/status_tracker.dart  Reçu → Confirmé → Transmis → Réparé
```
