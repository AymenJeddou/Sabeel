/// API base URL for the (temporary) glue backend -- see backend/app/README.md.
///
/// Edit this to match whatever machine is running `backend/app`'s uvicorn
/// server on your Wi-Fi network. Find it with `ipconfig` (Windows) and look
/// for the Wi-Fi adapter's IPv4 address. If the phone isn't on the same
/// network, use `ngrok http 8000` instead and paste the https URL here.
const String apiBaseUrl = 'http://10.214.7.180:8000';
