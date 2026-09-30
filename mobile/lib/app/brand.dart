import 'dart:ui' show PathMetric;

import 'package:flutter/material.dart';

/// Sabeel palette, taken from the logo canvas.
const sabeelNavy = Color(0xFF1B4F8F);
const sabeelCream = Color(0xFFF6F2EA);
const sabeelInk = Color(0xFF1D2023);
const sabeelAmber = Color(0xFFE8A317);
const sabeelTeal = Color(0xFF0F6E6A);
const sabeelMuted = Color(0xFF6B6A66);
const sabeelLine = Color(0xFFE9E2D4);

/// Report status wording and colour, shared with the authorities dashboard.
const statusLabels = {
  'new': 'Reçu',
  'confirmed': 'Confirmé',
  'sheet_sent': 'Transmis',
  'fixed': 'Réparé',
  'rejected': 'Classé',
};
const statusColors = {
  'new': Color(0xFF2F6DB5),
  'confirmed': Color(0xFFB7791F),
  'sheet_sent': Color(0xFFD0621B),
  'fixed': sabeelTeal,
  'rejected': sabeelMuted,
};

/// Severity 1-5 -> marker colour (same scale as the dashboard); grey = not scored.
Color severityColor(int? score) => score == null
    ? const Color(0xFF8A8F98)
    : const [
        Color(0xFF3E9E6B),
        Color(0xFF3E9E6B),
        Color(0xFFE0A21A),
        Color(0xFFE36A1B),
        Color(0xFFC8322B),
      ][score.clamp(1, 5) - 1];

/// Latin + Arabic body face and the kufi display face (bundled in assets/fonts).
const bodyFont = 'ReadexPro';
const displayFont = 'ReemKufi';

/// The Sabeel mark: a drop-shaped map pin with a road running through it.
/// Paths are the logo's SVG paths, in its 200x260 viewBox. [road] draws the
/// white road from 0 to 1 of its length; [dashOpacity]/[dashPhase] drive the
/// amber centre line (dash 11, gap 9, phase in viewBox units), so the splash
/// animation and the static logo share one painter.
class SabeelMarkPainter extends CustomPainter {
  const SabeelMarkPainter({
    this.road = 1,
    this.dashOpacity = 1,
    this.dashPhase = 0,
    this.color = sabeelNavy,
  });

  final double road;
  final double dashOpacity;
  final double dashPhase;
  final Color color;

  static final Path _pin = Path()
    ..moveTo(100, 250)
    ..cubicTo(64, 196, 20, 152, 20, 100)
    ..arcToPoint(
      const Offset(180, 100),
      radius: const Radius.circular(80),
      largeArc: true,
    )
    ..cubicTo(180, 152, 136, 196, 100, 250)
    ..close();

  static final PathMetric _roadMetric =
      (Path()
            ..moveTo(44, 206)
            ..cubicTo(44, 132, 154, 142, 154, 92)
            ..cubicTo(154, 58, 126, 36, 96, 26))
          .computeMetrics()
          .first;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / 200, size.height / 260);
    canvas.drawPath(_pin, Paint()..color = color);
    canvas.clipPath(_pin);

    final length = _roadMetric.length;
    if (road > 0) {
      canvas.drawPath(
        _roadMetric.extractPath(0, length * road),
        Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 28,
      );
    }
    if (dashOpacity > 0) {
      final dash = Paint()
        ..color = sabeelAmber.withValues(alpha: dashOpacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4;
      for (var s = dashPhase % 20 - 20; s < length; s += 20) {
        canvas.drawPath(_roadMetric.extractPath(s, s + 11), dash);
      }
    }
  }

  @override
  bool shouldRepaint(SabeelMarkPainter old) =>
      old.road != road ||
      old.dashOpacity != dashOpacity ||
      old.dashPhase != dashPhase ||
      old.color != color;
}

class SabeelMark extends StatelessWidget {
  const SabeelMark({super.key, this.height = 40});

  final double height;

  @override
  Widget build(BuildContext context) => CustomPaint(
    size: Size(height * 200 / 260, height),
    painter: const SabeelMarkPainter(),
  );
}

/// "Sabeel" set in Reem Kufi's Latin, so it reads as the same family as سبيل.
class SabeelWordmark extends StatelessWidget {
  const SabeelWordmark({super.key, this.fontSize = 26, this.color = sabeelInk});

  final double fontSize;
  final Color color;

  @override
  Widget build(BuildContext context) => Text(
    'Sabeel',
    style: TextStyle(
      fontFamily: displayFont,
      fontSize: fontSize,
      fontWeight: FontWeight.w600,
      letterSpacing: fontSize * 0.05,
      height: 1,
      color: color,
    ),
  );
}
