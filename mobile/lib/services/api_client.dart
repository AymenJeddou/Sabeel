import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/report_result.dart';
import 'location_service.dart';

/// All HTTP calls to the glue backend are isolated here so pointing at a
/// different backend later (e.g. real WP3, or a Cloud Run URL) is a one-file
/// change.
class RoadScanApiClient {
  Future<ReportResult> submitReport({
    required String deviceReportId,
    required LocationFix location,
    required File photo,
    required String source,
  }) async {
    final uri = Uri.parse('$apiBaseUrl/reports');
    final request = http.MultipartRequest('POST', uri);

    request.fields['device_report_id'] = deviceReportId;
    request.fields['lat'] = location.lat.toString();
    request.fields['lon'] = location.lon.toString();
    request.fields['gps_accuracy_m'] = location.accuracyM.toString();
    request.fields['speed_kmh'] = (location.speedKmh.isFinite && location.speedKmh > 0 ? location.speedKmh : 0.0).toString();
    request.fields['direction_deg'] = (location.directionDeg.isFinite && location.directionDeg >= 0 ? location.directionDeg : 0.0).toString();
    request.fields['captured_at'] = DateTime.now().toUtc().toIso8601String();
    request.fields['source'] = source;

    request.files.add(await http.MultipartFile.fromPath('photo', photo.path));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 201) {
      throw Exception('Report submission failed (${response.statusCode}): ${response.body}');
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return ReportResult.fromCreateResponse(json, deviceReportId);
  }

  Future<ReportResult> getReportStatus(String deviceReportId) async {
    final uri = Uri.parse('$apiBaseUrl/reports/$deviceReportId');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception('Status lookup failed (${response.statusCode}): ${response.body}');
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return ReportResult.fromStatusResponse(json, deviceReportId);
  }
}
