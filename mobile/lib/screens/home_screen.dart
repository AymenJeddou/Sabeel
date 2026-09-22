import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';

import '../services/mock_reports.dart';
import '../services/offline_queue_repository.dart';
import 'camera_capture_screen.dart';

const _cardShadow = [
  BoxShadow(color: Color(0x1A000000), blurRadius: 14, offset: Offset(0, 5)),
];

const _pillShadow = [
  BoxShadow(color: Color(0x26000000), blurRadius: 8, offset: Offset(0, 2)),
];

/// The Accueil tab (mobile/design/main.png).
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
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _Header(),
              const SizedBox(height: 16),
              SizedBox(
                height: 150,
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
              const SizedBox(height: 12),
              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: _StatCard(
                        value: '$pendingCount',
                        label: 'Rapports',
                        icon: Icons.warning_amber_rounded,
                        accent: const Color(0xFFC2510C),
                        background: const Color(0xFFFDF3D7),
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
                        accent: const Color(0xFF1B8A4B),
                        background: const Color(0xFFE8F7EE),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              _DrivingModeCard(onTap: () => _openDrivingModeStub(context)),
              const SizedBox(height: 16),
              _CameraCallToAction(onTap: () => _openCamera(context)),
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.star, color: Colors.white, size: 22),
            ),
            const SizedBox(width: 12),
            const Text(
              'RoadScan',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
            ),
          ],
        ),
        const SizedBox(height: 6),
        const Text(
          'Tunis · تونس',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: Colors.grey,
          ),
        ),
      ],
    );
  }
}

class _MapTile extends StatelessWidget {
  const _MapTile({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: _cardShadow,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Material(
          color: const Color(0xFFB9CEDD),
          child: InkWell(
            onTap: onTap,
            child: Stack(
              children: [
                const Positioned.fill(
                  child: CustomPaint(painter: _StreetGridPainter()),
                ),
                Align(
                  alignment: Alignment.bottomLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 16, right: 20),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.only(
                        topRight: Radius.circular(12),
                        bottomRight: Radius.circular(12),
                      ),
                      boxShadow: _pillShadow,
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Carte',
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                        SizedBox(width: 8),
                        Icon(Icons.map, size: 22, color: Color(0xFF1D6FE8)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ReportsTile extends StatelessWidget {
  const _ReportsTile({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: _cardShadow,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Material(
          color: const Color(0xFF25B866),
          child: Ink(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF2ECC80), Color(0xFF17A055)],
              ),
            ),
            child: InkWell(
              onTap: onTap,
              child: Stack(
                children: [
                  const Positioned(
                    top: 18,
                    right: 12,
                    child: _ChecklistGraphic(),
                  ),
                  Align(
                    alignment: Alignment.bottomRight,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 16, left: 16),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 10,
                      ),
                      decoration: const BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.only(
                          topLeft: Radius.circular(12),
                          bottomLeft: Radius.circular(12),
                        ),
                        boxShadow: _pillShadow,
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Rapports',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 16,
                            ),
                          ),
                          SizedBox(width: 6),
                          Icon(
                            Icons.chevron_right,
                            size: 24,
                            color: Color(0xFF17A055),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
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
        SizedBox(height: 10),
        _ChecklistRow(showCheck: true),
        SizedBox(height: 10),
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
    const faint = Color(0x59FFFFFF);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 24,
          child: showCheck
              ? const Icon(Icons.check, size: 20, color: faint)
              : null,
        ),
        const SizedBox(width: 8),
        Container(
          width: 64,
          height: 9,
          decoration: BoxDecoration(
            color: faint,
            borderRadius: BorderRadius.circular(5),
          ),
        ),
      ],
    );
  }
}

/// The stylised street map behind the "Carte" tile — decorative only,
/// standing in for the real map that lands in a later sprint. Wide avenues,
/// thinner side streets, a diagonal boulevard and a park block, so it reads
/// as a city rather than a plain grid.
class _StreetGridPainter extends CustomPainter {
  const _StreetGridPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(w * 0.63, h * 0.08, w * 0.27, h * 0.22),
        const Radius.circular(6),
      ),
      Paint()..color = const Color(0x808FC79A),
    );

    final avenue = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    final street = Paint()
      ..color = const Color(0xCCFFFFFF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(Offset(w * 0.36, -4), Offset(w * 0.36, h + 4), avenue);
    canvas.drawLine(Offset(-4, h * 0.46), Offset(w + 4, h * 0.46), avenue);

    canvas.drawLine(Offset(w * 0.74, -4), Offset(w * 0.74, h + 4), street);
    canvas.drawLine(Offset(-4, h * 0.18), Offset(w + 4, h * 0.18), street);
    canvas.drawLine(Offset(-4, h * 0.76), Offset(w + 4, h * 0.76), street);
    canvas.drawLine(Offset(w * 0.02, h + 4), Offset(w + 4, h * 0.26), street);
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
    required this.background,
  });

  final String value;
  final String label;
  final IconData icon;
  final Color accent;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(16),
        boxShadow: _cardShadow,
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: const BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 26, color: accent),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: accent,
                  ),
                ),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: accent,
                  ),
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
      color: const Color(0xFF2B3040),
      borderRadius: BorderRadius.circular(16),
      elevation: 4,
      shadowColor: const Color(0x552B3040),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: const Padding(
          padding: EdgeInsets.all(16),
          child: Row(
            children: [
              _CircleIcon(icon: Icons.drive_eta_outlined),
              SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Mode conduite',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 17,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Mains libres — un seul appui',
                      style: TextStyle(
                        color: Colors.white70,
                        fontWeight: FontWeight.w500,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.arrow_forward, color: Colors.white),
            ],
          ),
        ),
      ),
    );
  }
}

class _CircleIcon extends StatelessWidget {
  const _CircleIcon({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 40,
      alignment: Alignment.center,
      decoration: const BoxDecoration(
        color: Color(0x33FFFFFF),
        shape: BoxShape.circle,
      ),
      child: Icon(icon, color: Colors.white, size: 22),
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
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [
          BoxShadow(
            color: Color(0x401D6FE8),
            blurRadius: 18,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Material(
          color: const Color(0xFF1D6FE8),
          child: InkWell(
            onTap: onTap,
            child: Stack(
              children: [
                const Positioned.fill(
                  child: CustomPaint(painter: _DiagonalStripesPainter()),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(
                    vertical: 20,
                    horizontal: 16,
                  ),
                  // Stack gives non-positioned children loose constraints and
                  // aligns them top-start, so the column has to be forced to
                  // full width for its centered children to actually centre.
                  child: SizedBox(
                    width: double.infinity,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 58,
                          height: 58,
                          alignment: Alignment.center,
                          decoration: const BoxDecoration(
                            color: Color(0x33FFFFFF),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.camera_alt,
                            color: Colors.white,
                            size: 28,
                          ),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Signaler un nid-de-poule',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 21,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Une photo suffit — GPS automatique',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white70,
                            fontWeight: FontWeight.w500,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 22,
                            vertical: 11,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(26),
                            boxShadow: _pillShadow,
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                'Ouvrir la caméra',
                                style: TextStyle(
                                  color: Color(0xFF1D6FE8),
                                  fontWeight: FontWeight.w800,
                                  fontSize: 15,
                                ),
                              ),
                              SizedBox(width: 8),
                              Icon(
                                Icons.arrow_forward,
                                color: Color(0xFF1D6FE8),
                                size: 18,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Faint diagonal stripes across the camera call-to-action, matching the
/// texture in mobile/design/main.png.
class _DiagonalStripesPainter extends CustomPainter {
  const _DiagonalStripesPainter();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0x14FFFFFF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14;

    for (var x = -size.height; x < size.width; x += 34) {
      canvas.drawLine(
        Offset(x, size.height),
        Offset(x + size.height, 0),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
