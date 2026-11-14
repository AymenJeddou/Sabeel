import 'package:flutter/material.dart';

import '../app/brand.dart';

/// Reçu -> Confirmé -> Transmis -> Réparé (mobile/design/reports.png).
class StatusTracker extends StatelessWidget {
  const StatusTracker({super.key, required this.status});

  final String status;

  static const _steps = ['new', 'confirmed', 'sheet_sent', 'fixed'];

  @override
  Widget build(BuildContext context) {
    if (status == 'rejected') {
      return const Text(
        "Classé : ce n'était pas un nid-de-poule.",
        style: TextStyle(color: sabeelMuted, fontStyle: FontStyle.italic),
      );
    }
    // A reopened pothole is back in the queue, after confirmation.
    final reached = status == 'reopened' ? 1 : _steps.indexOf(status);
    final color = statusColors[status] ?? sabeelNavy;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var i = 0; i < _steps.length; i++) ...[
              if (i > 0)
                Expanded(
                  child: Container(
                    height: 3,
                    margin: const EdgeInsets.only(top: 10),
                    color: i <= reached ? color : sabeelLine,
                  ),
                ),
              Column(
                children: [
                  Container(
                    width: 22,
                    height: 22,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: i <= reached ? color : Colors.white,
                      border: Border.all(
                        color: i <= reached ? color : sabeelLine,
                        width: 2,
                      ),
                    ),
                    child: i <= reached
                        ? const Icon(Icons.check, size: 13, color: Colors.white)
                        : null,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    statusLabels[_steps[i]]!,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: i == reached
                          ? FontWeight.w700
                          : FontWeight.w500,
                      color: i <= reached ? sabeelInk : sabeelMuted,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
        if (status == 'reopened')
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text(
              'Rouvert : des citoyens indiquent qu’il est toujours là.',
              style: TextStyle(
                fontSize: 12,
                color: Color(0xFFC8322B),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
      ],
    );
  }
}
