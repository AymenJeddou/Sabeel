import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';

import 'rules.dart';

/// Copies a captured photo into permanent app storage so it survives OS
/// cache eviction while the report waits to upload.
Future<String> keepPhoto(String sourcePath, String deviceReportId) async {
  final dir = Directory(
    '${(await getApplicationDocumentsDirectory()).path}/reports',
  );
  if (!await dir.exists()) await dir.create(recursive: true);
  final path = '${dir.path}/$deviceReportId.jpg';
  await File(sourcePath).copy(path);
  return path;
}

/// Laplacian variance of a 400 px wide grayscale copy, computed in an isolate
/// (issue #33). Null if the file can't be decoded.
Future<double?> sharpness(String path) => compute(_sharpness, path);

double? _sharpness(String path) {
  final decoded = img.decodeImage(File(path).readAsBytesSync());
  if (decoded == null) return null;
  final small = img.grayscale(img.copyResize(decoded, width: 400));
  final gray = [for (final p in small) p.r.toInt()];
  return laplacianVariance(gray, small.width, small.height);
}

/// Driving mode: a 640 px JPEG of a camera frame for POST /detect.
Future<Uint8List?> shrinkForDetection(String path) => compute(_shrink, path);

Uint8List? _shrink(String path) {
  final raw = img.decodeImage(File(path).readAsBytesSync());
  if (raw == null) return null;
  // Phones store portrait shots sideways plus an EXIF rotation tag; re-encoding drops the
  // tag, so apply it first or the model sees the road on its side.
  final decoded = img.bakeOrientation(raw);
  final resized = decoded.width > 640
      ? img.copyResize(decoded, width: 640)
      : decoded;
  return Uint8List.fromList(img.encodeJpg(resized, quality: 80));
}

bool looksBlurry(double? variance) =>
    variance != null && variance < blurThreshold;
