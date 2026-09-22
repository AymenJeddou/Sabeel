import 'package:flutter/material.dart';

import '../models/report_result.dart';
import '../services/api_client.dart';

/// Shown after a report is successfully submitted to the Core API: severity,
/// status, and -- once WP2's RAG service has run -- the routed office and the
/// generated work sheet.
class ReportResultScreen extends StatefulWidget {
  const ReportResultScreen({super.key, required this.result});

  final ReportResult result;

  @override
  State<ReportResultScreen> createState() => _ReportResultScreenState();
}

class _ReportResultScreenState extends State<ReportResultScreen> {
  final _apiClient = const RoadScanApiClient();

  late ReportResult _result;
  bool _refreshing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _result = widget.result;
  }

  Future<void> _refreshStatus() async {
    setState(() {
      _refreshing = true;
      _error = null;
    });
    try {
      final updated = await _apiClient.getReportStatus(_result.deviceReportId);
      if (!mounted) return;
      setState(() => _result = updated);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'new':
        return Colors.grey;
      case 'confirmed':
        return Colors.orange;
      case 'sheet_sent':
        return Colors.blue;
      case 'fixed':
        return Colors.green;
      default:
        return Colors.black;
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'new':
        return 'Nouveau';
      case 'confirmed':
        return 'Confirmé';
      case 'sheet_sent':
        return 'Fiche envoyée';
      case 'fixed':
        return 'Réparé';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    final score = _result.score;

    return Scaffold(
      appBar: AppBar(title: const Text('Résultat du signalement')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Chip(
                        label: Text(_statusLabel(_result.status)),
                        backgroundColor: _statusColor(_result.status).withValues(alpha: 0.2),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        score != null ? 'Sévérité : $score / 5' : 'Aucun nid de poule détecté',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (_result.targetOffice != null) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Transmis à', style: Theme.of(context).textTheme.labelMedium),
                    Text(_result.targetOffice!, style: Theme.of(context).textTheme.titleMedium),
                  ],
                ),
              ),
            ),
          ],
          if (_result.sheetSummary != null) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Fiche de travaux', style: Theme.of(context).textTheme.labelMedium),
                    const SizedBox(height: 8),
                    Text(_result.sheetSummary!),
                  ],
                ),
              ),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: _refreshing ? null : _refreshStatus,
            icon: _refreshing
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.refresh),
            label: const Text('Actualiser le statut'),
          ),
        ],
      ),
    );
  }
}
