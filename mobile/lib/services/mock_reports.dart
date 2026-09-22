import '../models/queued_report.dart';
import '../models/report_draft.dart';

/// Stand-in for the city-wide "réparés" counter until WP3's API can serve
/// the real figure. Shown in debug builds only; release shows a dash.
const mockRepairedCount = 312;

/// Sample reports around Tunis so the list and counters aren't empty while
/// developing. Seeded in debug builds only (see main.dart), and their ids
/// carry the `mock-` prefix so [OfflineQueueRepository] never writes them to
/// the real offline queue on disk.
List<QueuedReport> buildMockReports() {
  final now = DateTime.now().toUtc();

  QueuedReport sample({
    required String id,
    required String locationLabel,
    required double lat,
    required double lon,
    required double gpsAccuracyM,
    required double speedKmh,
    required double directionDeg,
    required int minutesAgo,
  }) {
    final capturedAt = now.subtract(Duration(minutes: minutesAgo));
    return QueuedReport(
      draft: ReportDraft(
        deviceReportId: id,
        lat: lat,
        lon: lon,
        gpsAccuracyM: gpsAccuracyM,
        speedKmh: speedKmh,
        directionDeg: directionDeg,
        capturedAt: capturedAt,
        source: ReportSource.manual,
      ),
      photoPath: '',
      queuedAt: capturedAt,
      locationLabel: locationLabel,
    );
  }

  return [
    sample(
      id: 'mock-2847a1b2',
      locationLabel: 'Av. Habib Bourguiba, Tunis',
      lat: 36.8008,
      lon: 10.1817,
      gpsAccuracyM: 4.2,
      speedKmh: 0,
      directionDeg: 182,
      minutesAgo: 12,
    ),
    sample(
      id: 'mock-2831c3d4',
      locationLabel: 'Rue de Marseille, Tunis',
      lat: 36.7992,
      lon: 10.1765,
      gpsAccuracyM: 6.5,
      speedKmh: 38.5,
      directionDeg: 274,
      minutesAgo: 95,
    ),
    sample(
      id: 'mock-2819e5f6',
      locationLabel: 'Blvd du 7 Novembre, Tunis',
      lat: 36.8412,
      lon: 10.2001,
      gpsAccuracyM: 3.1,
      speedKmh: 12.4,
      directionDeg: 44,
      minutesAgo: 320,
    ),
    sample(
      id: 'mock-2803a7b8',
      locationLabel: 'Av. de la République, Tunis',
      lat: 36.7788,
      lon: 10.1690,
      gpsAccuracyM: 8.0,
      speedKmh: 0,
      directionDeg: 97,
      minutesAgo: 1450,
    ),
  ];
}
