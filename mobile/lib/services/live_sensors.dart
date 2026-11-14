import 'dart:async';

import 'package:flutter_compass/flutter_compass.dart';
import 'package:geolocator/geolocator.dart';

import 'location_service.dart';

/// Keeps the latest GPS fix and compass heading while the camera is open, so
/// nothing waits on location after the shutter (issue #33: report in < 15 s).
class LiveSensors {
  StreamSubscription<Position>? _position;
  StreamSubscription<CompassEvent>? _compass;
  LocationSnapshot? latest;
  double? _heading;
  final _updates = StreamController<LocationSnapshot>.broadcast();

  Stream<LocationSnapshot> get updates => _updates.stream;

  /// Starts the GPS and compass streams. Throws [LocationServiceException]
  /// when location is off or refused (the message explains why it's needed).
  Future<void> start() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const LocationServiceException(
        'La localisation est désactivée. Active le GPS pour continuer.',
      );
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw const LocationServiceException(
        'Sabeel a besoin de la position pour placer le nid-de-poule et l’envoyer au bon service. '
        'Elle ne sert jamais à suivre vos trajets.',
      );
    }
    _compass = FlutterCompass.events?.listen((e) => _heading = e.heading);
    _position =
        Geolocator.getPositionStream(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.best,
            distanceFilter: 0,
          ),
        ).listen((p) {
          final heading = _heading ?? (p.heading >= 0 ? p.heading : 0);
          latest = LocationSnapshot(
            lat: p.latitude,
            lon: p.longitude,
            gpsAccuracyM: p.accuracy,
            speedKmh: p.speed > 0 ? p.speed * 3.6 : 0,
            directionDeg: (heading % 360 + 360) % 360,
            capturedAt: DateTime.now().toUtc(),
          );
          _updates.add(latest!);
        });
  }

  /// The latest fix if it is younger than [maxAge] (default 10 s), else null.
  LocationSnapshot? fresh({
    Duration maxAge = const Duration(seconds: 10),
    DateTime? now,
  }) => isFresh(latest, maxAge: maxAge, now: now) ? latest : null;

  Future<void> stop() async {
    await _position?.cancel();
    await _compass?.cancel();
    await _updates.close();
  }
}

/// Freshness rule for a sensor snapshot (unit-tested).
bool isFresh(
  LocationSnapshot? s, {
  Duration maxAge = const Duration(seconds: 10),
  DateTime? now,
}) =>
    s != null &&
    (now ?? DateTime.now().toUtc()).difference(s.capturedAt) <= maxAge;
