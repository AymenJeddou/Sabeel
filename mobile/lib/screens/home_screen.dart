import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';

import '../app/brand.dart';
import '../services/mock_reports.dart';
import '../services/offline_queue_repository.dart';
import 'camera_capture_screen.dart';

/// The Accueil tab (mobile/design/main.png, restyled to the Sabeel brand).
///
/// The mockup's "1284 signalements / 312 réparés" stat cards are city-wide
/// aggregates that only the backend (WP3) can provide, and driving mode is
/// explicitly deferred past this sprint — both are represented honestly
/// below rather than faked.
class HomeScreen extends StatelessWidget {
  const HomeScreen({
    super.key,
    required this.queueRepository,
    required this.onNavigateToTab,
  });

  final OfflineQueueRepository queueRepository;
  final ValueChanged<int> onNavigateToTab;

  void _openDrivingModeStub(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Mode conduite — bientôt disponible.')),
    );
  }

  Future<void> _openCamera(BuildContext context) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CameraCaptureScreen(queueRepository: queueRepository),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: queueRepository,
      builder: (context, _) {
        final pendingCount = queueRepository.queue.length;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _Header(),
              const SizedBox(height: 20),
              _CameraCallToAction(onTap: () => _openCamera(context)),
              const SizedBox(height: 14),
              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: _StatCard(
                        value: '$pendingCount',
                        label: 'Rapports',
                        icon: Icons.warning_amber_rounded,
                        accent: const Color(0xFFA86F06),
                        tint: sabeelAmber.withValues(alpha: 0.16),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _StatCard(
                        // Real figure comes from WP3's API; debug shows the
                        // sample number so the screen reads like the design.
                        value: kDebugMode ? '$mockRepairedCount' : '—',
                        label: 'Réparés',
                        icon: Icons.check_circle_outline,
                        accent: sabeelTeal,
                        tint: sabeelTeal.withValues(alpha: 0.12),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                height: 132,
                child: Row(
                  children: [
                    Expanded(child: _MapTile(onTap: () => onNavigateToTab(1))),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _ReportsTile(onTap: () => onNavigateToTab(2)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              _DrivingModeCard(onTap: () => _openDrivingModeStub(context)),
            ],
          ),
        );
      },
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        SabeelMark(height: 44),
        SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SabeelWordmark(fontSize: 28),
            SizedBox(height: 4),
            Text(
              'سبيل · Tunis',
              style: TextStyle(fontSize: 13, color: sabeelMuted),
            ),
          ],
        ),
      ],
    );
  }
}

/// A tile with the shared rounded shape and ripple.
class _Tile extends StatelessWidget {
  const _Tile({required this.color, required this.onTap, required this.child});

  final Color color;
  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: InkWell(onTap: onTap, child: child),
    );
  }
}

/// Label chip on the Carte / Rapports tiles.
class _TileLabel extends StatelessWidget {
  const _TileLabel({
    required this.text,
    required this.icon,
    required this.color,
  });

  final String text;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            text,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
          ),
          const SizedBox(width: 6),
          Icon(icon, size: 20, color: color),
        ],
      ),
    );
  }
}

class _MapTile extends StatelessWidget {
  const _MapTile({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return _Tile(
      color: const Color(0xFFE7E0D1),
      onTap: onTap,
      child: const Stack(
        children: [
          Positioned.fill(child: CustomPaint(painter: _StreetGridPainter())),
          Positioned(top: 22, right: 30, child: SabeelMark(height: 34)),
          Align(
            alignment: Alignment.bottomLeft,
            child: _TileLabel(
              text: 'Carte',
              icon: Icons.map_outlined,
              color: sabeelNavy,
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportsTile extends StatelessWidget {
  const _ReportsTile({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return _Tile(
      color: sabeelTeal,
      onTap: onTap,
      child: const Stack(
        children: [
          Positioned(top: 18, right: 14, child: _ChecklistGraphic()),
          Align(
            alignment: Alignment.bottomLeft,
            child: _TileLabel(
              text: 'Rapports',
              icon: Icons.chevron_right,
              color: sabeelTeal,
            ),
          ),
        ],
      ),
    );
  }
}

class _ChecklistGraphic extends StatelessWidget {
  const _ChecklistGraphic();

  @override
  Widget build(BuildContext context) {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: [
        _ChecklistRow(showCheck: true),
        SizedBox(height: 9),
        _ChecklistRow(showCheck: true),
        SizedBox(height: 9),
        _ChecklistRow(showCheck: false),
      ],
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow({required this.showCheck});

  final bool showCheck;

  @override
  Widget build(BuildContext context) {
    const faint = Color(0x4DFFFFFF);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 22,
          child: showCheck
              ? const Icon(Icons.check, size: 18, color: sabeelAmber)
              : null,
        ),
        const SizedBox(width: 6),
        Container(
          width: 56,
          height: 8,
          decoration: BoxDecoration(
            color: faint,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
      ],
    );
  }
}

/// The stylised street map behind the "Carte" tile — decorative only.
/// Wide avenues, thinner side streets, a curving boulevard and a park block,
/// so it reads as a city rather than a plain grid.
class _StreetGridPainter extends CustomPainter {
  const _StreetGridPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(w * 0.06, h * 0.08, w * 0.24, h * 0.24),
        const Radius.circular(8),
      ),
      Paint()..color = const Color(0xFFCFDDC9),
    );

    final avenue = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;
    final street = Paint()
      ..color = const Color(0xB3FFFFFF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(Offset(w * 0.40, -4), Offset(w * 0.40, h + 4), street);
    canvas.drawLine(Offset(-4, h * 0.42), Offset(w + 4, h * 0.42), street);
    canvas.drawLine(Offset(-4, h * 0.78), Offset(w + 4, h * 0.78), street);
    canvas.drawPath(
      Path()
        ..moveTo(-4, h * 0.95)
        ..cubicTo(w * 0.35, h * 0.9, w * 0.55, h * 0.2, w + 4, h * 0.12),
      avenue,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.value,
    required this.label,
    required this.icon,
    required this.accent,
    required this.tint,
  });

  final String value;
  final String label;
  final IconData icon;
  final Color accent;
  final Color tint;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: sabeelLine),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: tint,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, size: 24, color: accent),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    height: 1.1,
                  ),
                ),
                Text(
                  label,
                  style: const TextStyle(fontSize: 12, color: sabeelMuted),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DrivingModeCard extends StatelessWidget {
  const _DrivingModeCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: sabeelInk,
      borderRadius: BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: sabeelAmber,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(
                  Icons.drive_eta_outlined,
                  color: sabeelInk,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Mode conduite',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Mains libres — un seul appui',
                      style: TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward, color: Colors.white70),
            ],
          ),
        ),
      ),
    );
  }
}

class _CameraCallToAction extends StatelessWidget {
  const _CameraCallToAction({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: sabeelNavy.withValues(alpha: 0.28),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Material(
        color: sabeelNavy,
        borderRadius: BorderRadius.circular(24),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Stack(
            children: [
              // The logo's pin and road, oversized and ghosted, as texture.
              const Positioned(
                right: -26,
                bottom: -40,
                child: Opacity(
                  opacity: 0.35,
                  child: CustomPaint(
                    size: Size(150, 195),
                    painter: SabeelMarkPainter(color: Color(0xFF0E3566)),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Signaler un nid-de-poule',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Une photo suffit — GPS automatique',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                    const SizedBox(height: 18),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 18,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.photo_camera, color: sabeelNavy, size: 20),
                          SizedBox(width: 8),
                          Text(
                            'Ouvrir la caméra',
                            style: TextStyle(
                              color: sabeelNavy,
                              fontWeight: FontWeight.w600,
                              fontSize: 15,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
