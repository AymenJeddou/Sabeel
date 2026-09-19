import 'package:geolocator/geolocator.dart';

class LocationFix {
  final double lat;
  final double lon;
  final double accuracyM;
  final double speedKmh;
  final double directionDeg;

  LocationFix({
    required this.lat,
    required this.lon,
    required this.accuracyM,
    required this.speedKmh,
    required this.directionDeg,
  });
}

class LocationService {
  Future<LocationFix> getCurrentFix() async {
    final permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      final requested = await Geolocator.requestPermission();
      if (requested == LocationPermission.denied || requested == LocationPermission.deniedForever) {
        throw Exception('Location permission is required to submit a report.');
      }
    }

    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled.');
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );

    return LocationFix(
      lat: position.latitude,
      lon: position.longitude,
      accuracyM: position.accuracy,
      speedKmh: (position.speed) * 3.6, // m/s -> km/h
      directionDeg: position.heading,
    );
  }
}
