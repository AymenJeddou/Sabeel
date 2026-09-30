import 'package:flutter/material.dart';

import '../app/brand.dart';

/// Opening animation, a frame-accurate port of the logo canvas's
/// Splash.dc.html: pin drops and bounces, road draws itself, the amber centre
/// line fades in and flows, then سبيل reveals right-to-left and "Sabeel"
/// left-to-right. Same keyframes, delays and cubic-bezier easings as the CSS
/// (Flutter's Curves.easeOut/easeInOut are CSS ease-out/ease-in-out).
/// Tap anywhere to skip.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key, required this.next});

  final WidgetBuilder next;

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

// Timeline in ms, straight from the CSS animations.
const _total = 2800; // 2500 of animation + a short hold on the finished logo.
const _dropCurve = Cubic(0.3, 0.7, 0.4, 1);

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: _total),
  )..forward();
  bool _left = false;

  @override
  void initState() {
    super.initState();
    _controller.addStatusListener((s) {
      if (s == AnimationStatus.completed) _leave();
    });
  }

  void _leave() {
    if (_left) return;
    _left = true;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 450),
        pageBuilder: (context, _, _) => widget.next(context),
        transitionsBuilder: (_, animation, _, child) =>
            FadeTransition(opacity: animation, child: child),
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: sabeelCream,
      body: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: _leave,
        child: Center(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, _) =>
                _SplashFrame(ms: _controller.value * _total),
          ),
        ),
      ),
    );
  }
}

class _SplashFrame extends StatelessWidget {
  const _SplashFrame({required this.ms});

  final double ms;

  /// 0..1 progress of an animation that starts at [start] and lasts [dur].
  double _t(double start, double dur) => ((ms - start) / dur).clamp(0.0, 1.0);

  @override
  Widget build(BuildContext context) {
    // sb-drop / sb-shadow: 750ms from 0, easing applied per keyframe segment.
    final drop = _t(0, 750);
    final ty = _keyframes(
      drop,
      const [0, .55, .68, .80, .90, 1],
      const [-260, 0, 0, -16, 0, 0],
      _dropCurve,
    );
    final sx = _keyframes(
      drop,
      const [0, .55, .68, .80, .90, 1],
      const [1, 1, 1.1, .96, 1.02, 1],
      _dropCurve,
    );
    final sy = _keyframes(
      drop,
      const [0, .55, .68, .80, .90, 1],
      const [1, 1, .88, 1.05, .98, 1],
      _dropCurve,
    );
    final pinOpacity = _keyframes(
      drop,
      const [0, .12, 1],
      const [0, 1, 1],
      _dropCurve,
    );
    final shadowScale = _keyframes(
      drop,
      const [0, .55, .80, 1],
      const [0, 1.1, .85, 1],
      Curves.easeOut,
    );
    final shadowOpacity = _keyframes(
      drop,
      const [0, .55, .80, 1],
      const [0, .22, .14, .18],
      Curves.easeOut,
    );

    // sb-road, sb-dash (fade + 900ms linear flow of 20 units), sb-ar, sb-en.
    final road = Curves.easeInOut.transform(_t(700, 700));
    final dashOpacity = Curves.easeOut.transform(_t(1350, 250));
    final dashPhase = ms > 1350 ? (ms - 1350) / 900 * 20 : 0.0;
    final ar = Curves.easeOut.transform(_t(1550, 650));
    final en = Curves.easeOut.transform(_t(2000, 500));

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Opacity(
          opacity: pinOpacity,
          child: Transform(
            alignment: Alignment.bottomCenter,
            transform: Matrix4.identity()
              ..translateByDouble(0, ty, 0, 1)
              ..scaleByDouble(sx, sy, 1, 1),
            child: CustomPaint(
              size: const Size(140, 182),
              painter: SabeelMarkPainter(
                road: road,
                dashOpacity: dashOpacity,
                dashPhase: dashPhase,
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Opacity(
          opacity: shadowOpacity,
          child: Transform.scale(
            scale: shadowScale,
            child: Container(
              width: 56,
              height: 10,
              decoration: const BoxDecoration(
                color: sabeelInk,
                borderRadius: BorderRadius.all(Radius.elliptical(28, 5)),
              ),
            ),
          ),
        ),
        const SizedBox(height: 28),
        // clip-path inset(0 0 0 100%) -> 0: revealed from the right edge.
        Opacity(
          opacity: 0.2 + 0.8 * ar,
          child: ClipRect(
            clipper: _Reveal(ar, fromRight: true),
            child: const Text(
              'سبيل',
              textDirection: TextDirection.rtl,
              style: TextStyle(
                fontFamily: displayFont,
                fontSize: 84,
                fontWeight: FontWeight.w700,
                height: 1.15,
                color: sabeelNavy,
              ),
            ),
          ),
        ),
        const SizedBox(height: 2),
        Opacity(
          opacity: en,
          child: Transform.translate(
            offset: Offset(0, 8 * (1 - en)),
            child: ClipRect(
              clipper: _Reveal(en, fromRight: false),
              child: const SabeelWordmark(fontSize: 42),
            ),
          ),
        ),
      ],
    );
  }
}

/// Piecewise keyframe interpolation with [curve] applied inside each segment,
/// the way a CSS animation-timing-function works.
double _keyframes(double p, List<double> at, List<double> v, Curve curve) {
  for (var i = 0; i < at.length - 1; i++) {
    if (p <= at[i + 1]) {
      final local = (p - at[i]) / (at[i + 1] - at[i]);
      return v[i] + (v[i + 1] - v[i]) * curve.transform(local);
    }
  }
  return v.last;
}

class _Reveal extends CustomClipper<Rect> {
  const _Reveal(this.t, {required this.fromRight});

  final double t;
  final bool fromRight;

  @override
  Rect getClip(Size size) => fromRight
      ? Rect.fromLTRB(size.width * (1 - t), 0, size.width, size.height)
      : Rect.fromLTRB(0, 0, size.width * t, size.height);

  @override
  bool shouldReclip(_Reveal old) => old.t != t;
}
