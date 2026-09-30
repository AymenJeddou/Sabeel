import 'dart:io';

import 'package:flutter/material.dart';

import '../app/brand.dart';
import '../models/queued_report.dart';
import '../services/offline_queue_repository.dart';

const _frenchMonths = [
  'janv.',
  'févr.',
  'mars',
  'avr.',
  'mai',
  'juin',
  'juil.',
  'août',
  'sept.',
  'oct.',
  'nov.',
  'déc.',
];

String _formatDate(DateTime utc) {
  final local = utc.toLocal();
  return '${local.day} ${_frenchMonths[local.month - 1]} ${local.year}';
}

/// The Mes signalements tab (mobile/design/reports.png).
///
/// The mockup's 4-step status tracker (Reçu/Confirmé/Transmis/Réparé)
/// depends on WP3's API assigning a real status — until there is a
/// backend to upload to, every queued report is simply "pending upload".
class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key, required this.queueRepository});

  final OfflineQueueRepository queueRepository;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: queueRepository,
      builder: (context, _) {
        final reports = queueRepository.queue;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Mes Rapports',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${reports.length} rapport(s) depuis cet appareil',
                    style: const TextStyle(color: sabeelMuted),
                  ),
                ],
              ),
            ),
            Expanded(
              child: reports.isEmpty
                  ? const _EmptyState()
                  : ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                      itemCount: reports.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 12),
                      itemBuilder: (context, index) =>
                          _ReportCard(report: reports[index]),
                    ),
            ),
          ],
        );
      },
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inbox_outlined, size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(
              "Aucun signalement pour le moment.\nUtilise le bouton caméra depuis l'accueil.",
              textAlign: TextAlign.center,
              style: const TextStyle(color: sabeelMuted),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReportCard extends StatelessWidget {
  const _ReportCard({required this.report});

  final QueuedReport report;

  @override
  Widget build(BuildContext context) {
    final draft = report.draft;
    final photoFile = File(report.photoPath);

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: sabeelLine),
      ),
      padding: const EdgeInsets.all(12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: SizedBox(
              width: 64,
              height: 64,
              child: photoFile.existsSync()
                  ? Image.file(photoFile, fit: BoxFit.cover)
                  : Container(
                      color: Colors.grey.shade200,
                      child: const Icon(Icons.image_not_supported_outlined),
                    ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  report.locationLabel ??
                      '${draft.lat.toStringAsFixed(5)}, ${draft.lon.toStringAsFixed(5)}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  '${report.reference} · ${_formatDate(draft.capturedAt)}',
                  style: const TextStyle(fontSize: 12, color: sabeelMuted),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: sabeelAmber.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text(
                    "En attente d'envoi",
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
