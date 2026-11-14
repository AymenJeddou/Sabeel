import 'dart:io';

import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../app/brand.dart';
import '../models/queued_report.dart';
import '../models/report_draft.dart';
import '../services/location_service.dart';
import '../services/photo_tools.dart';
import '../services/sabeel_data.dart';
import 'report_result_screen.dart';

/// "Mode détaillé": shown right after a photo is captured. Acquires
/// GPS/speed/compass, shows every contract field, and sends the report once
/// the citizen confirms (stored locally first, retried if offline).
class ReportPreviewScreen extends StatefulWidget {
  const ReportPreviewScreen({
    super.key,
    required this.photoPath,
    required this.data,
  });

  final String photoPath;
  final SabeelData data;

  @override
  State<ReportPreviewScreen> createState() => _ReportPreviewScreenState();
}

class _ReportPreviewScreenState extends State<ReportPreviewScreen> {
  final LocationService _locationService = LocationService();
  final Uuid _uuid = Uuid();

  ReportDraft? _draft;
  String? _errorMessage;
  bool _isCapturingLocation = true;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _captureSensorData();
  }

  Future<void> _captureSensorData() async {
    setState(() {
      _isCapturingLocation = true;
      _errorMessage = null;
    });
    try {
      final snapshot = await _locationService.captureSnapshot();
      final draft = ReportDraft(
        deviceReportId: _uuid.v4(),
        lat: snapshot.lat,
        lon: snapshot.lon,
        gpsAccuracyM: snapshot.gpsAccuracyM,
        speedKmh: snapshot.speedKmh,
        directionDeg: snapshot.directionDeg,
        capturedAt: snapshot.capturedAt,
        source: ReportSource.manual,
      );
      debugPrint('[RoadScan] New report captured: ${draft.toApiJson()}');
      if (!mounted) return;
      setState(() {
        _draft = draft;
        _isCapturingLocation = false;
      });
    } on LocationServiceException catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.message;
        _isCapturingLocation = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Erreur inattendue lors de la lecture GPS.';
        _isCapturingLocation = false;
      });
    }
  }

  Future<void> _confirm() async {
    final draft = _draft;
    if (draft == null || _isSaving) return;
    setState(() => _isSaving = true);
    try {
      final path = await keepPhoto(widget.photoPath, draft.deviceReportId);
      final stored = await widget.data.submit(
        QueuedReport(
          draft: draft,
          photoPath: path,
          queuedAt: DateTime.now().toUtc(),
        ),
      );
      if (!mounted || stored == null) return;
      Navigator.of(context).popUntil((route) => route.isFirst);
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) =>
              ReportResultScreen(data: widget.data, reportId: stored.id),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Impossible d'enregistrer le signalement."),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vérifier le signalement')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.file(
                File(widget.photoPath),
                height: 220,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(height: 16),
            _buildStatus(),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _isSaving
                        ? null
                        : () => Navigator.of(context).pop(),
                    child: const Text('Reprendre'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: (_draft != null && !_isSaving) ? _confirm : null,
                    child: _isSaving
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text('Confirmer'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatus() {
    if (_isCapturingLocation) {
      return const Row(
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          SizedBox(width: 12),
          Text('Lecture GPS, vitesse et cap en cours…'),
        ],
      );
    }

    final errorMessage = _errorMessage;
    if (errorMessage != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.error_outline, color: Colors.redAccent),
              const SizedBox(width: 8),
              Expanded(child: Text(errorMessage)),
            ],
          ),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _captureSensorData,
            child: const Text('Réessayer'),
          ),
        ],
      );
    }

    final draft = _draft;
    if (draft == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: sabeelLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _InfoRow(label: 'Latitude', value: draft.lat.toStringAsFixed(6)),
          _InfoRow(label: 'Longitude', value: draft.lon.toStringAsFixed(6)),
          _InfoRow(
            label: 'Précision GPS',
            value: '${draft.gpsAccuracyM.toStringAsFixed(1)} m',
          ),
          _InfoRow(
            label: 'Vitesse',
            value: '${draft.speedKmh.toStringAsFixed(1)} km/h',
          ),
          _InfoRow(
            label: 'Direction',
            value: '${draft.directionDeg.toStringAsFixed(0)}°',
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: sabeelMuted)),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
