import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

/// Anonymous, persistent id for this phone: ties "Mes Rapports" and the
/// support chat to the citizen without an account. Sent with every report.
String deviceId = 'unregistered';

Future<void> initDeviceId(SharedPreferences prefs) async {
  deviceId = prefs.getString('device_id') ?? const Uuid().v4();
  await prefs.setString('device_id', deviceId);
}
