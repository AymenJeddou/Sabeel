import 'package:flutter/material.dart';

import '../app/brand.dart';
import '../models/queued_report.dart';
import '../services/sabeel_data.dart';
import 'reports_screen.dart';

/// One report's page: where it stands, and the choice the citizen has to
/// make when the model saw no pothole ("Reprendre" / "Envoyer quand même").
class ReportResultScreen extends StatelessWidget {
  const ReportResultScreen({
    super.key,
    required this.data,
    required this.reportId,
  });

  final SabeelData data;
  final String reportId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mon signalement')),
      body: ListenableBuilder(
        listenable: data,
        builder: (context, _) {
          final r = data.queue.byId(reportId);
          if (r == null) {
            return const Center(child: Text('Signalement supprimé.'));
          }
          return RefreshIndicator(
            onRefresh: data.refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (r.notDetected)
                  _NotDetected(data: data, report: r)
                else
                  ReportCard(report: r, data: data),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _NotDetected extends StatelessWidget {
  const _NotDetected({required this.data, required this.report});

  final SabeelData data;
  final QueuedReport report;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(
              Icons.visibility_off_outlined,
              size: 36,
              color: sabeelMuted,
            ),
            const SizedBox(height: 12),
            const Text(
              'Aucun nid-de-poule détecté',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            const Text(
              'Le modèle ne voit pas de nid-de-poule sur cette photo. Reprenez-la de plus près, '
              'ou envoyez-la quand même : un agent la vérifiera.',
              style: TextStyle(color: sabeelMuted, height: 1.4),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () async {
                      await data.resolveNotDetected(
                        report.id,
                        sendAnyway: false,
                      );
                      if (context.mounted) Navigator.of(context).pop();
                    },
                    child: const Text('Reprendre'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () =>
                        data.resolveNotDetected(report.id, sendAnyway: true),
                    child: const Text('Envoyer quand même'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
