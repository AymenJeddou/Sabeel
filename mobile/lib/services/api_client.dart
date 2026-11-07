import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/remote_report.dart';
import '../models/report_draft.dart';
import '../models/report_result.dart';
import 'device.dart';

/// Thrown when the Core API is unreachable or answers with an error.
/// [statusCode] is null when the server could not be reached at all.
class ApiClientException implements Exception {
  const ApiClientException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  /// Worth retrying later (offline, timeout, server trouble, rate limit).
  bool get retryable =>
      statusCode == null || statusCode! >= 500 || statusCode == 429;

  @override
  String toString() => message;
}

/// Result of scoring one driving-mode frame (POST /detect).
class FrameDetection {
  const FrameDetection({required this.detected, this.score, this.confidence});
  final bool detected;
  final int? score;
  final double? confidence;
}

/// Counts returned after an "I see it too"-style tap.
class ConfirmationResult {
  const ConfirmationResult({
    required this.created,
    required this.status,
    required this.confirmCount,
  });
  final bool created;
  final String status;
  final int confirmCount;
}

/// All HTTP calls to the Core API live here, so pointing at another backend
/// is a one-line change (`--dart-define=API_BASE_URL=...`).
class RoadScanApiClient {
  const RoadScanApiClient({this.timeout = const Duration(seconds: 30)});

  final Duration timeout;

  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call().timeout(timeout);
    } on SocketException {
      throw const ApiClientException('Serveur injoignable.');
    } on http.ClientException {
      throw const ApiClientException('Serveur injoignable.');
    } on HandshakeException {
      throw const ApiClientException('Connexion sécurisée impossible.');
    } on TimeoutException {
      throw const ApiClientException('Le serveur ne répond pas.');
    }
  }

  static String _detail(http.Response r) {
    try {
      final detail = (jsonDecode(utf8.decode(r.bodyBytes)) as Map)['detail'];
      if (detail is String) return detail;
    } catch (_) {}
    return 'Erreur serveur (${r.statusCode}).';
  }

  /// POST /reports. Idempotent on device_report_id: a retry returns 200 with
  /// the same report. `force` = "Envoyer quand même" after detected=false.
  Future<ReportResult> submitReport({
    required ReportDraft draft,
    required String photoPath,
    bool force = false,
  }) => _guard(() async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$apiBaseUrl/reports'),
    );
    draft.toApiJson().forEach(
      (key, value) => request.fields[key] = value.toString(),
    );
    request.fields['device_id'] = deviceId;
    if (force) request.fields['force'] = 'true';
    request.files.add(await http.MultipartFile.fromPath('photo', photoPath));
    final response = await http.Response.fromStream(await request.send());
    if (response.statusCode == 429) {
      throw const ApiClientException(
        'Trop de signalements, réessai plus tard.',
        statusCode: 429,
      );
    }
    if (response.statusCode != 201 && response.statusCode != 200) {
      throw ApiClientException(
        _detail(response),
        statusCode: response.statusCode,
      );
    }
    final json =
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    return ReportResult.fromJson(json, deviceReportId: draft.deviceReportId);
  });

  Future<dynamic> _getJson(String path) => _guard(() async {
    final response = await http.get(Uri.parse('$apiBaseUrl$path'));
    if (response.statusCode != 200) {
      throw ApiClientException(
        _detail(response),
        statusCode: response.statusCode,
      );
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  });

  Future<dynamic> _postJson(String path, Map<String, dynamic> body) =>
      _guard(() async {
        final response = await http.post(
          Uri.parse('$apiBaseUrl$path'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        );
        if (response.statusCode != 200 && response.statusCode != 201) {
          throw ApiClientException(
            _detail(response),
            statusCode: response.statusCode,
          );
        }
        return jsonDecode(utf8.decode(response.bodyBytes));
      });

  /// Every report this phone sent, with its pothole's current status.
  Future<List<MyReport>> fetchMyReports() async => [
    for (final json in await _getJson('/devices/$deviceId/reports') as List)
      MyReport.fromJson(json as Map<String, dynamic>),
  ];

  /// Potholes in the visible map area (bbox = minLon,minLat,maxLon,maxLat).
  Future<List<MapPothole>> fetchMap({
    String? bbox,
    String? sev,
    String? state,
  }) async {
    final query = {'bbox': ?bbox, 'sev': ?sev, 'state': ?state};
    final path = Uri(
      path: '/map',
      queryParameters: query.isEmpty ? null : query,
    ).toString();
    return [
      for (final json in await _getJson(path) as List)
        MapPothole.fromJson(json as Map<String, dynamic>),
    ];
  }

  /// Public city-wide figures (GET /public/stats).
  Future<Map<String, dynamic>> fetchStats() async =>
      await _getJson('/public/stats') as Map<String, dynamic>;

  /// "Je le vois aussi" (seen), "Toujours là" (not_fixed), "Bien réparé"
  /// (fixed_ok), "Pas un nid-de-poule" (not_pothole).
  Future<ConfirmationResult> confirm({
    required String potholeId,
    required String kind,
    required double lat,
    required double lon,
    required double accuracyM,
  }) async {
    final json =
        await _postJson('/potholes/$potholeId/confirmations', {
              'device_id': deviceId,
              'kind': kind,
              'lat': lat,
              'lon': lon,
              'gps_accuracy_m': accuracyM,
            })
            as Map<String, dynamic>;
    return ConfirmationResult(
      created: json['created'] as bool,
      status: json['status'] as String,
      confirmCount: json['confirm_count'] as int,
    );
  }

  /// Driving mode: scores one JPEG frame; the server stores nothing.
  Future<FrameDetection> detect(Uint8List jpeg) => _guard(() async {
    final request =
        http.MultipartRequest('POST', Uri.parse('$apiBaseUrl/detect'))
          ..fields['device_id'] = deviceId
          ..fields['source'] = 'driving_mode'
          ..files.add(
            http.MultipartFile.fromBytes('frame', jpeg, filename: 'frame.jpg'),
          );
    final response = await http.Response.fromStream(await request.send());
    if (response.statusCode != 200) {
      throw ApiClientException(
        _detail(response),
        statusCode: response.statusCode,
      );
    }
    final json =
        jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    return FrameDetection(
      detected: json['detected'] as bool,
      score: json['score'] as int?,
      confidence: (json['confidence'] as num?)?.toDouble(),
    );
  });

  Future<List<ChatMessage>> fetchMessages() async => [
    for (final json in await _getJson('/messages?device_id=$deviceId') as List)
      ChatMessage.fromJson(json as Map<String, dynamic>),
  ];

  Future<void> sendMessage(String body) async {
    await _postJson('/messages', {
      'device_id': deviceId,
      'sender': 'citizen',
      'body': body,
    });
  }
}
