import 'dart:math' as math;

/// Pure rules shared by the services and screens (unit-tested, no plugins).

/// Upload retry schedule (issue #31): 30 s, 2 min, 10 min, then every hour.
Duration backoffFor(int attempts) {
  const steps = [
    Duration(seconds: 30),
    Duration(minutes: 2),
    Duration(minutes: 10),
    Duration(hours: 1),
  ];
  return steps[math.min(math.max(attempts - 1, 0), steps.length - 1)];
}

/// When to retry: the backoff schedule, or the server's Retry-After if longer
/// (retrying earlier would only be refused again).
Duration retryDelay(int attempts, Duration? retryAfter) {
  final backoff = backoffFor(attempts);
  return retryAfter != null && retryAfter > backoff ? retryAfter : backoff;
}

/// Statuses that deserve a notification, with the message to show.
const notifyMessages = {
  'confirmed': 'Votre signalement est confirmé par d’autres citoyens.',
  'sheet_sent': 'La fiche de travaux a été transmise au service compétent.',
  'fixed': 'Votre signalement a été réparé, merci !',
  'reopened': 'Le nid-de-poule est rouvert : les services sont relancés.',
};

/// Compares the last known status of each report with the server's and
/// returns the (deviceReportId, newStatus) pairs worth a notification.
List<(String, String)> statusChanges(
  Map<String, String?> before,
  Map<String, String> after,
) => [
  for (final e in after.entries)
    if (before.containsKey(e.key) &&
        before[e.key] != null &&
        before[e.key] != e.value &&
        notifyMessages.containsKey(e.value))
      (e.key, e.value),
];

const _earthM = 6371000.0;
double _rad(double d) => d * math.pi / 180;

/// Great-circle distance in metres.
double distanceM(double lat1, double lon1, double lat2, double lon2) {
  final dLat = _rad(lat2 - lat1), dLon = _rad(lon2 - lon1);
  final a =
      math.pow(math.sin(dLat / 2), 2) +
      math.cos(_rad(lat1)) *
          math.cos(_rad(lat2)) *
          math.pow(math.sin(dLon / 2), 2);
  // Rounding can push a just above 1 for near-antipodal points: asin would return NaN.
  return 2 * _earthM * math.asin(math.min(1.0, math.sqrt(a.toDouble())));
}

/// Initial bearing from point 1 to point 2, 0-360°.
double bearingDeg(double lat1, double lon1, double lat2, double lon2) {
  final y = math.sin(_rad(lon2 - lon1)) * math.cos(_rad(lat2));
  final x =
      math.cos(_rad(lat1)) * math.sin(_rad(lat2)) -
      math.sin(_rad(lat1)) * math.cos(_rad(lat2)) * math.cos(_rad(lon2 - lon1));
  return (math.atan2(y, x) * 180 / math.pi + 360) % 360;
}

/// Same geofence as the server (issue #22): within 50 m, GPS better than 40 m.
/// Returns null when allowed, else the reason to show.
String? geofenceReason(double distanceM, double accuracyM) {
  if (accuracyM > 40) {
    return 'Position trop imprécise (±${accuracyM.round()} m)';
  }
  if (distanceM - accuracyM > 50) {
    return 'Rapprochez-vous du nid-de-poule (à ${distanceM.round()} m)';
  }
  return null;
}

/// Driving mode: a pothole is "ahead" when it is within [rangeM] and within
/// [coneDeg] of the direction of travel.
bool isAhead({
  required double lat,
  required double lon,
  required double headingDeg,
  required double targetLat,
  required double targetLon,
  double rangeM = 200,
  double coneDeg = 30,
}) {
  final d = distanceM(lat, lon, targetLat, targetLon);
  if (d > rangeM || d < 5) return false;
  final diff =
      (bearingDeg(lat, lon, targetLat, targetLon) - headingDeg).abs() % 360;
  return math.min(diff, 360 - diff) <= coneDeg;
}

/// Driving mode capture gate (cahier F6): only between 5 and 80 km/h.
bool shouldCapture(double speedKmh) => speedKmh >= 5 && speedKmh <= 80;

/// Driving mode confirmation: a pothole is reported after 3 positive frames in a row.
class ConsecutiveDetector {
  ConsecutiveDetector({this.needed = 3});

  final int needed;
  int _streak = 0;

  int get streak => _streak;

  /// Feeds one frame result; true exactly when the streak reaches [needed].
  bool add(bool positive) {
    _streak = positive ? _streak + 1 : 0;
    if (_streak == needed) return true;
    return false;
  }

  void reset() => _streak = 0;
}

/// Grid clustering for the map (5,000+ points stay smooth). Groups points by
/// cell; the cell size halves at each zoom level. Returns lists of indices.
List<List<int>> clusterIndices(
  List<(double, double)> points,
  double zoom, {
  double cellPxAtZoom = 60,
}) {
  if (zoom >= 17) {
    return [
      for (var i = 0; i < points.length; i++) [i],
    ];
  }
  final degPerPx = 360 / (256 * math.pow(2, zoom));
  final cell = cellPxAtZoom * degPerPx;
  final cells = <String, List<int>>{};
  for (var i = 0; i < points.length; i++) {
    final (lat, lon) = points[i];
    final key = '${(lat / cell).floor()}:${(lon / cell).floor()}';
    (cells[key] ??= []).add(i);
  }
  return cells.values.toList();
}

/// Sharpness of a grayscale image: variance of the Laplacian (higher = sharper).
double laplacianVariance(List<int> gray, int width, int height) {
  if (width < 3 || height < 3) return 0;
  var sum = 0.0, sumSq = 0.0, n = 0;
  for (var y = 1; y < height - 1; y++) {
    for (var x = 1; x < width - 1; x++) {
      final i = y * width + x;
      final v =
          4 * gray[i] -
          gray[i - 1] -
          gray[i + 1] -
          gray[i - width] -
          gray[i + width];
      sum += v;
      sumSq += v * v;
      n++;
    }
  }
  final mean = sum / n;
  return sumSq / n - mean * mean;
}

/// Below this Laplacian variance (on a 400 px wide grayscale copy) a photo is
/// probably blurred. Starting value from the OpenCV literature (≈100); M3
/// asks to calibrate it on 10 real photos: see mobile/README.md.
const blurThreshold = 100.0;
