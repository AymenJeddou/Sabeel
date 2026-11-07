import 'package:flutter_test/flutter_test.dart';

import 'package:roadscan_mobile/services/live_sensors.dart';
import 'package:roadscan_mobile/services/location_service.dart';
import 'package:roadscan_mobile/services/rules.dart';

void main() {
  test('backoff schedule: 30 s, 2 min, 10 min, then 1 h', () {
    expect(backoffFor(1), const Duration(seconds: 30));
    expect(backoffFor(2), const Duration(minutes: 2));
    expect(backoffFor(3), const Duration(minutes: 10));
    expect(backoffFor(4), const Duration(hours: 1));
    expect(backoffFor(12), const Duration(hours: 1));
  });

  test('status diff notifies only real changes to notifiable states', () {
    final changes = statusChanges(
      {'a': 'new', 'b': 'confirmed', 'c': 'sheet_sent', 'd': null, 'e': 'new'},
      {
        'a': 'confirmed',
        'b': 'confirmed',
        'c': 'fixed',
        'd': 'fixed',
        'e': 'rejected',
        'z': 'fixed',
      },
    );
    expect(changes, [('a', 'confirmed'), ('c', 'fixed')]);
  });

  test('geofence: 50 m and GPS better than 40 m, like the server', () {
    expect(geofenceReason(30, 5), isNull);
    expect(geofenceReason(80, 35), isNull); // within reach given the accuracy
    expect(geofenceReason(200, 5), contains('Rapprochez-vous'));
    expect(geofenceReason(10, 60), contains('imprécise'));
  });

  test('distance and bearing', () {
    expect(distanceM(36.8, 10.18, 36.8009, 10.18), closeTo(100, 1));
    expect(bearingDeg(36.8, 10.18, 36.81, 10.18), closeTo(0, 0.5));
    expect(bearingDeg(36.8, 10.18, 36.8, 10.19), closeTo(90, 0.5));
  });

  test('pothole ahead only in front and in range', () {
    bool ahead(double heading, double lat) => isAhead(
      lat: 36.8,
      lon: 10.18,
      headingDeg: heading,
      targetLat: lat,
      targetLon: 10.18,
    );
    expect(ahead(0, 36.8012), isTrue); // 133 m north, driving north
    expect(ahead(180, 36.8012), isFalse); // behind
    expect(ahead(0, 36.805), isFalse); // 555 m: too far
  });

  test('driving mode captures only between 5 and 80 km/h', () {
    expect(shouldCapture(0), isFalse);
    expect(shouldCapture(30), isTrue);
    expect(shouldCapture(95), isFalse);
  });

  test('3 consecutive positive frames confirm, a miss resets', () {
    final d = ConsecutiveDetector();
    expect(
      [true, true, false, true, true].map(d.add).toList(),
      everyElement(isFalse),
    );
    expect(d.add(true), isTrue);
  });

  test('clustering groups close points and splits at high zoom', () {
    final pts = [(36.8, 10.18), (36.8001, 10.1801), (36.9, 10.3)];
    expect(clusterIndices(pts, 10).length, 2);
    expect(clusterIndices(pts, 18).length, 3);
    final many = [
      for (var i = 0; i < 5000; i++)
        (36.7 + (i % 100) * 0.002, 10.1 + (i ~/ 100) * 0.004),
    ];
    expect(clusterIndices(many, 11).length, lessThan(500));
  });

  test('blur metric: flat image ~0, sharp edges high', () {
    final flat = List.filled(20 * 20, 128);
    final edges = [for (var i = 0; i < 400; i++) (i % 2 == 0) ? 0 : 255];
    expect(laplacianVariance(flat, 20, 20), 0);
    expect(laplacianVariance(edges, 20, 20), greaterThan(blurThreshold));
  });

  test('sensor snapshot freshness: 10 s rule', () {
    final now = DateTime.utc(2026, 11, 7, 12);
    LocationSnapshot at(int secondsAgo) => LocationSnapshot(
      lat: 36.8,
      lon: 10.18,
      gpsAccuracyM: 5,
      speedKmh: 0,
      directionDeg: 0,
      capturedAt: now.subtract(Duration(seconds: secondsAgo)),
    );
    expect(isFresh(at(3), now: now), isTrue);
    expect(isFresh(at(11), now: now), isFalse);
    expect(isFresh(null, now: now), isFalse);
  });
}
