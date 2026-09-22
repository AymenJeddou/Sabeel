import 'package:flutter_test/flutter_test.dart';
import 'package:roadscan_mobile/utils/iso8601.dart';

void main() {
  test('formats a UTC DateTime with trailing Z and no fractional seconds', () {
    final dt = DateTime.utc(2026, 9, 15, 10, 32, 0, 123);
    expect(toContractIso8601Utc(dt), '2026-09-15T10:32:00Z');
  });

  test('converts a local DateTime to UTC before formatting', () {
    final local = DateTime(2026, 9, 15, 12, 32, 0);
    // Compare against formatting the same instant already converted to UTC,
    // rather than asserting an absolute offset, so this doesn't depend on
    // the test runner's local timezone.
    expect(toContractIso8601Utc(local), toContractIso8601Utc(local.toUtc()));
  });

  test('pads single-digit month/day/hour/minute/second', () {
    final dt = DateTime.utc(2026, 1, 2, 3, 4, 5);
    expect(toContractIso8601Utc(dt), '2026-01-02T03:04:05Z');
  });
}
