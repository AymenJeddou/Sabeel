import 'package:flutter/material.dart';

import '../models/report_result.dart';
import '../services/api_client.dart';

class ResultScreen extends StatefulWidget {
  final ReportResult result;

  const ResultScreen({super.key, required this.result});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  late ReportResult _result;
  bool _refreshing = false;
  String? _error;

  final _apiClient = RoadScanApiClient();

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
      setState(() => _result = updated);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _refreshing = false);
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

  @override
  Widget build(BuildContext context) {
    final score = _result.score;

    return Scaffold(
      appBar: AppBar(title: const Text('Report result')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Report ID', style: Theme.of(context).textTheme.labelMedium),
                    Text(_result.reportId, style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Chip(
                          label: Text(_result.status),
                          backgroundColor: _statusColor(_result.status).withValues(alpha: 0.2),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          score != null ? 'Severity: $score / 5' : 'No pothole detected',
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
                      Text('Routed to', style: Theme.of(context).textTheme.labelMedium),
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
                      Text('Work sheet', style: Theme.of(context).textTheme.labelMedium),
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
              label: const Text('Refresh status'),
            ),
          ],
        ),
      ),
    );
  }
}
