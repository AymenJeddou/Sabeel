import 'dart:io';

import 'package:flutter/material.dart';

import '../app/brand.dart';
import '../config.dart';
import '../models/queued_report.dart';
import '../models/remote_report.dart';
import '../services/sabeel_data.dart';
import '../widgets/status_tracker.dart';
import 'report_result_screen.dart';
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

String formatDate(DateTime utc) {
  final local = utc.toLocal();
  return '${local.day} ${_frenchMonths[local.month - 1]} ${local.year}';
}

/// The Mes Rapports tab (issue #31): every report this phone made, uploaded
/// or not, with its live 4-step tracker. Failed uploads show when the next
/// automatic retry happens and a "Réessayer" button.
class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key, required this.data});

  final SabeelData data;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: data,
      builder: (context, _) {
        final local = data.queue.queue;
        final others = data.serverOnly;
        final total = local.length + others.length;
        final waiting = data.queue.pending.length;
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
                          [
                            '$total rapport(s)',
                            if (waiting > 0) '$waiting en attente d’envoi',
                            if (!data.online && total > 0) 'hors ligne',
                          ].join(' · '),
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
                          for (final r in local) ...[
                            ReportCard(report: r, data: data),
                            const SizedBox(height: 12),
                          ],
                          for (final r in others) ...[
                            _ServerCard(report: r),
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
  Widget build(BuildContext context) => Padding(
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

class _Frame extends StatelessWidget {
  const _Frame({required this.photo, required this.children, this.onTap});

  final Widget photo;
  final List<Widget> children;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
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

Widget _noPhoto() => Container(
  color: Colors.grey.shade200,
  child: const Icon(Icons.image_not_supported_outlined),
);

/// One stored report: upload state, then the server tracker once uploaded.
class ReportCard extends StatelessWidget {
  const ReportCard({super.key, required this.report, required this.data});

  final QueuedReport report;
  final SabeelData data;

  @override
  Widget build(BuildContext context) {
    final r = report;
    final file = File(r.photoPath);
    final severity = r.severity;
    return _Frame(
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ReportResultScreen(data: data, reportId: r.id),
        ),
      ),
      photo: file.existsSync()
          ? Image.file(file, fit: BoxFit.cover)
          : _noPhoto(),
      children: [
        Text(
          r.locationLabel ??
              '${r.draft.lat.toStringAsFixed(5)}, ${r.draft.lon.toStringAsFixed(5)}',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Expanded(
              child: Text(
                [
                  r.reference,
                  formatDate(r.draft.capturedAt),
                  if (severity != null) 'sévérité $severity/5',
                  if (r.draft.source.wireValue == 'driving_mode')
                    'mode conduite',
                ].join(' · '),
                style: const TextStyle(fontSize: 12, color: sabeelMuted),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (r.isUploaded)
              InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: () =>
                    _openChat(context, 'À propos de ${r.reference} : '),
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
        if (r.notDetected)
          const _Pill(
            text: 'Aucun nid-de-poule détecté — touchez pour choisir',
            color: Color(0xFFB7791F),
          )
        else if (!r.isUploaded) ...[
          _Pill(
            text: switch (r.uploadState) {
              UploadState.uploading => 'Envoi en cours…',
              UploadState.failed => 'Refusé : ${r.lastError ?? 'erreur'}',
              _ =>
                r.attempts == 0
                    ? 'Envoi en attente'
                    : 'Envoi en attente · nouvel essai ${_when(r.nextAttemptAt)}',
            },
            color: r.uploadState == UploadState.failed
                ? const Color(0xFFC8322B)
                : sabeelAmber,
          ),
          if (r.uploadState != UploadState.uploading)
            TextButton.icon(
              onPressed: () =>
                  data.flushUploads(onlyId: r.id, ignoreSchedule: true),
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Réessayer'),
            ),
        ] else
          StatusTracker(status: r.status ?? 'new'),
      ],
    );
  }

  static String _when(DateTime? at) {
    if (at == null) return 'bientôt';
    final d = at.difference(DateTime.now().toUtc());
    if (d.inSeconds <= 0) return 'imminent';
    if (d.inMinutes < 1) return 'dans ${d.inSeconds} s';
    if (d.inHours < 1) return 'dans ${d.inMinutes} min';
    return 'dans ${d.inHours} h';
  }
}

class _ServerCard extends StatelessWidget {
  const _ServerCard({required this.report});

  final MyReport report;

  @override
  Widget build(BuildContext context) {
    final r = report;
    return _Frame(
      photo: r.photoUrl == null
          ? _noPhoto()
          : Image.network(
              r.photoUrl!.startsWith('http')
                  ? r.photoUrl!
                  : '$apiBaseUrl${r.photoUrl}',
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => _noPhoto(),
            ),
      children: [
        Text(
          r.addressLabel ??
              '${r.lat.toStringAsFixed(5)}, ${r.lon.toStringAsFixed(5)}',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 4),
        Text(
          '${r.ref ?? '—'} · ${formatDate(r.createdAt)}',
          style: const TextStyle(fontSize: 12, color: sabeelMuted),
        ),
        const SizedBox(height: 10),
        StatusTracker(status: r.status),
      ],
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.16),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Text(
      text,
      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
    ),
  );
}
