/// API base URL for the (temporary) glue backend -- see backend/app/README.md.
///
/// `10.0.2.2` is the Android emulator's special alias for the host
/// machine's `localhost` -- use this while testing on an emulator.
///
/// For a REAL physical phone on the same Wi-Fi network, replace this with
/// the host machine's LAN IPv4 address instead (find it with `ipconfig` on
/// Windows, look for the Wi-Fi adapter). If the phone isn't on the same
/// network, use `ngrok http 8000` instead and paste the https URL here.
const String apiBaseUrl = 'http://10.0.2.2:8000';
