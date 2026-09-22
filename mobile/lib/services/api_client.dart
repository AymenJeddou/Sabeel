import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/report_draft.dart';
import '../models/report_result.dart';

/// Thrown when the Core API is unreachable or returns an error. Callers
/// should treat this as "stays in the offline queue for later," never as a
/// reason to lose the report.
class ApiClientException implements Exception {
  const ApiClientException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// All HTTP calls to WP3's Core API are isolated here so pointing at a
/// different backend (a real deploy, an ngrok tunnel) is a one-file change.
class RoadScanApiClient {
  const RoadScanApiClient({this.timeout = const Duration(seconds: 30)});

  final Duration timeout;

  Future<ReportResult> submitReport({
    required ReportDraft draft,
    required String photoPath,
  }) async {
    final uri = Uri.parse('$apiBaseUrl/reports');
    final request = http.MultipartRequest('POST', uri);

    final fields = draft.toApiJson();
    fields.forEach((key, value) => request.fields[key] = value.toString());

    request.files.add(await http.MultipartFile.fromPath('photo', photoPath));

    try {
      final streamedResponse = await request.send().timeout(timeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 201) {
        throw ApiClientException(
          'Le serveur a refusé le signalement (${response.statusCode}).',
        );
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return ReportResult.fromJson(json, deviceReportId: draft.deviceReportId);
    } on SocketException {
      throw const ApiClientException('Serveur injoignable.');
    } on http.ClientException {
      throw const ApiClientException('Serveur injoignable.');
    }
  }

  Future<ReportResult> getReportStatus(String deviceReportId) async {
    final uri = Uri.parse('$apiBaseUrl/reports/$deviceReportId');
    final response = await http.get(uri).timeout(timeout);

    if (response.statusCode != 200) {
      throw ApiClientException(
        'Impossible de récupérer le statut (${response.statusCode}).',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return ReportResult.fromJson(json, deviceReportId: deviceReportId);
  }
}
