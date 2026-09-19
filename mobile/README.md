# RoadScan mobile — minimal insurance client (Sprint 1)

Minimal Flutter app (camera/gallery capture + GPS + one API call + result
screen) built by Aymen during Sprint 1 so a real end-to-end mobile demo
exists regardless of WP4's own timeline — see issue #5. Android-only for now
(no iOS toolchain risk). Jed — happy to hand off or pair on the fuller WP4
build (map screen, offline queue, driving mode) in Sprint 2.

## Setup

Edit `lib/config.dart` to point `apiBaseUrl` at whatever machine is running
`backend/app`'s uvicorn server on your Wi-Fi network (find the IP with
`ipconfig`). If the phone isn't on the same network, run `ngrok http 8000`
and paste the https URL there instead.

```bash
flutter pub get
flutter run   # pick an Android emulator or connected device
```

## Known gaps vs. real WP4

No offline queue, no map screen, no driving mode, no local persistence of
past reports — `device_report_id` is generated fresh each app launch. All
HTTP calls are isolated in `lib/services/api_client.dart` so pointing at a
different backend, or handing this off to a fuller implementation, is a
small, contained change.
