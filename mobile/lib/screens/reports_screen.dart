import 'dart:io';

import 'package:flutter/material.dart';

import '../app/brand.dart';
import '../config.dart';
import '../models/queued_report.dart';
import '../models/remote_report.dart';
import '../services/sabeel_data.dart';
import 'map_screen.dart';
import 'support_chat_screen.dart';

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

/// The Mes Rapports tab (mobile/design/reports.png): reports still waiting to
/// upload, then this phone's reports on the server with their live status
/// (the same status the authorities set on the dashboard).
class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key, required this.data});

  final SabeelData data;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: data,
      builder: (context, _) {
        final pending = data.queue.queue;
        final sent = data.mine;
        final total = pending.length + sent.length;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Mes Rapports',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          data.online || total == 0
                              ? '$total rapport(s) depuis cet appareil'
                              : '$total rapport(s) · hors ligne',
                          style: const TextStyle(color: sabeelMuted),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Assistance',
                    icon: const Icon(Icons.support_agent, color: sabeelTeal),
                    onPressed: () => _openChat(context),
                  ),
                ],
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: data.refresh,
                child: total == 0
                    ? ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: const [SizedBox(height: 80), _EmptyState()],
                      )
                    : ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                        children: [
                          for (final r in pending) ...[
                            _PendingCard(report: r),
                            const SizedBox(height: 12),
                          ],
                          for (final r in sent) ...[
                            _SentCard(report: r),
                            const SizedBox(height: 12),
                          ],
                        ],
                      ),
              ),
            ),
          ],
        );
      },
    );
  }
}

void _openChat(BuildContext context, [String initialText = '']) {
  Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => SupportChatScreen(initialText: initialText),
    ),
  );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.inbox_outlined, size: 48, color: Colors.grey.shade400),
          const SizedBox(height: 12),
          const Text(
            "Aucun signalement pour le moment.\nUtilise le bouton caméra depuis l'accueil.",
            textAlign: TextAlign.center,
            style: TextStyle(color: sabeelMuted),
          ),
        ],
      ),
    );
  }
}

/// Shared card frame: photo on the left, text on the right.
class _Card extends StatelessWidget {
  const _Card({required this.photo, required this.children, this.onTap});

  final Widget photo;
  final List<Widget> children;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: sabeelLine),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: SizedBox(width: 64, height: 64, child: photo),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: children,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

Widget _noPhoto() => Container(
  color: Colors.grey.shade200,
  child: const Icon(Icons.image_not_supported_outlined),
);

class _PendingCard extends StatelessWidget {
  const _PendingCard({required this.report});

  final QueuedReport report;

  @override
  Widget build(BuildContext context) {
    final draft = report.draft;
    final photoFile = File(report.photoPath);
    return _Card(
      photo: photoFile.existsSync()
          ? Image.file(photoFile, fit: BoxFit.cover)
          : _noPhoto(),
      children: [
        Text(
          report.locationLabel ??
              '${draft.lat.toStringAsFixed(5)}, ${draft.lon.toStringAsFixed(5)}',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 4),
        Text(
          '${report.reference} · ${_formatDate(draft.capturedAt)}',
          style: const TextStyle(fontSize: 12, color: sabeelMuted),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: sabeelAmber.withValues(alpha: 0.18),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Text(
            "En attente d'envoi — renvoyé automatiquement",
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}

class _SentCard extends StatelessWidget {
  const _SentCard({required this.report});

  final RemoteReport report;

  @override
  Widget build(BuildContext context) {
    final r = report;
    return _Card(
      onTap: () => showPotholeSheet(context, r),
      photo: r.photoUrl == null
          ? _noPhoto()
          : Image.network(
              '$apiBaseUrl${r.photoUrl}',
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => _noPhoto(),
            ),
      children: [
        Text(
          r.address ??
              '${r.lat.toStringAsFixed(5)}, ${r.lon.toStringAsFixed(5)}',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Expanded(
              child: Text(
                '${r.ref} · ${_formatDate(r.createdAt)}'
                '${r.score != null ? ' · sévérité ${r.score}/5' : ''}',
                style: const TextStyle(fontSize: 12, color: sabeelMuted),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: () => _openChat(context, 'À propos de ${r.ref} : '),
              child: const Padding(
                padding: EdgeInsets.all(4),
                child: Icon(
                  Icons.chat_bubble_outline,
                  size: 18,
                  color: sabeelTeal,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        StatusTracker(status: r.status),
      ],
    );
  }
}
