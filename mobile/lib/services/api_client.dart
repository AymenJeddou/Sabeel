import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/report_draft.dart';
import '../models/remote_report.dart';
import '../models/report_result.dart';
import 'device.dart';

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
    request.fields['device_id'] = deviceId;

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

  Future<dynamic> _getJson(String path) async {
    try {
      final response = await http
          .get(Uri.parse('$apiBaseUrl$path'))
          .timeout(timeout);
      if (response.statusCode != 200) {
        throw ApiClientException('Erreur serveur (${response.statusCode}).');
      }
      return jsonDecode(utf8.decode(response.bodyBytes));
    } on SocketException {
      throw const ApiClientException('Serveur injoignable.');
    } on http.ClientException {
      throw const ApiClientException('Serveur injoignable.');
    }
  }

  /// Every report, newest first (one call feeds the map and "Mes Rapports").
  Future<List<RemoteReport>> fetchReports() async => [
    for (final json in await _getJson('/reports') as List)
      RemoteReport.fromJson(json as Map<String, dynamic>),
  ];

  /// City-wide figures (backend insights.compute_stats).
  Future<Map<String, dynamic>> fetchStats() async =>
      await _getJson('/stats') as Map<String, dynamic>;

  Future<List<ChatMessage>> fetchMessages() async => [
    for (final json in await _getJson('/messages?device_id=$deviceId') as List)
      ChatMessage.fromJson(json as Map<String, dynamic>),
  ];

  Future<void> sendMessage(String body) async {
    try {
      final response = await http
          .post(
            Uri.parse('$apiBaseUrl/messages'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'device_id': deviceId,
              'sender': 'citizen',
              'body': body,
            }),
          )
          .timeout(timeout);
      if (response.statusCode != 201) {
        throw ApiClientException(
          "Message non envoyé (${response.statusCode}).",
        );
      }
    } on SocketException {
      throw const ApiClientException('Serveur injoignable.');
    } on http.ClientException {
      throw const ApiClientException('Serveur injoignable.');
    }
  }
}
