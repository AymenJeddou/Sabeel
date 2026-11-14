import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:uuid/uuid.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import '../app/brand.dart';
import '../models/queued_report.dart';
import '../models/report_draft.dart';
import '../services/live_sensors.dart';
import '../services/location_service.dart';
import '../services/photo_tools.dart';
import '../services/rules.dart';
import '../services/sabeel_data.dart';
import 'report_preview_screen.dart';
import 'report_result_screen.dart';

/// The camera, in three modes:
///
/// - **quick** (default, issue #33): GPS and compass start with the camera;
///   the shutter builds the report from the latest fix (< 10 s old), checks
///   the photo for blur, then shows "Envoyé dans 5 s · Annuler". Nothing is
///   uploaded during that window, so cancelling leaves nothing on the server.
/// - **detailed**: the Sprint 1 flow with the GPS/speed/compass preview.
/// - **driving** (cahier F6): phone on the windscreen. One frame every
///   [_frameEvery] between 5 and 80 km/h is scored by POST /detect (nothing
///   stored); 3 positive frames in a row upload a `driving_mode` report. Known
///   potholes ahead are announced by voice and vibration.
class CameraCaptureScreen extends StatefulWidget {
  const CameraCaptureScreen({
    super.key,
    required this.data,
    this.drivingMode = false,
    this.detailed = false,
  });

  final SabeelData data;
  final bool drivingMode;
  final bool detailed;

  @override
  State<CameraCaptureScreen> createState() => _CameraCaptureScreenState();
}

class _CameraCaptureScreenState extends State<CameraCaptureScreen>
    with WidgetsBindingObserver {
  static const _frameEvery = Duration(milliseconds: 1500);
  static const _undoWindow = Duration(seconds: 5);

  CameraController? _controller;
  Future<void>? _initializeControllerFuture;
  String? _errorMessage;
  String? _sensorError;
  bool _isSettingUp = false;
  final _sensors = LiveSensors();
  final _stopwatch = Stopwatch()..start();
  final _timings = <String, int>{};

  // Driving mode
  Timer? _frameTimer;
  final _detector = ConsecutiveDetector();
  bool _scoring = false;
  int _framesScored = 0;
  int _autoReports = 0;
  String _drivingStatus = 'Démarrage…';
  final _tts = FlutterTts();
  final _announced = <String>{};
  StreamSubscription<LocationSnapshot>? _aheadSub;
  (double, double)? _loadedAround;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _setupCamera();
    _sensors.start().catchError((Object e) {
      if (mounted) setState(() => _sensorError = e.toString());
    });
    if (widget.drivingMode) _startDriving();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _frameTimer?.cancel();
    _aheadSub?.cancel();
    _sensors.stop();
    _controller?.dispose();
    if (widget.drivingMode) WakelockPlus.disable();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden) {
      _teardownCamera();
    } else if (state == AppLifecycleState.resumed && _controller == null) {
      _setupCamera();
    }
  }

  void _teardownCamera() {
    final controller = _controller;
    if (controller == null) return;
    _controller = null;
    _initializeControllerFuture = null;
    controller.dispose();
    if (mounted) setState(() {});
  }

  Future<void> _setupCamera() async {
    if (_isSettingUp) return;
    _isSettingUp = true;
    try {
      final cameras = await availableCameras();
      if (!mounted) return;
      if (cameras.isEmpty) {
        setState(
          () => _errorMessage = 'Aucune caméra disponible sur cet appareil.',
        );
        return;
      }
      final back = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        back,
        widget.drivingMode ? ResolutionPreset.medium : ResolutionPreset.high,
        enableAudio: false,
      );
      final initializeFuture = controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
        _initializeControllerFuture = initializeFuture;
        _errorMessage = null;
      });
      await initializeFuture;
      _timings['camera_ready_ms'] = _stopwatch.elapsedMilliseconds;
      if (mounted) setState(() {});
    } on CameraException catch (e) {
      if (!mounted) return;
      setState(() => _errorMessage = _messageForCameraException(e));
    } finally {
      _isSettingUp = false;
    }
  }

  String _messageForCameraException(CameraException e) => switch (e.code) {
    'CameraAccessDenied' ||
    'CameraAccessDeniedWithoutPrompt' ||
    'CameraAccessRestricted' =>
      'Permission caméra refusée. Active-la dans les réglages du téléphone.',
    _ => "Impossible d'ouvrir la caméra (${e.code}).",
  };

  // ---------------------------------------------------------------- quick

  Future<void> _capture() async {
    final controller = _controller;
    if (controller == null ||
        !controller.value.isInitialized ||
        controller.value.isTakingPicture) {
      return;
    }
    final XFile file;
    try {
      file = await controller.takePicture();
    } on CameraException catch (e) {
      if (mounted) _snack('Erreur de capture (${e.code}).');
      return;
    }
    _timings['shutter_ms'] = _stopwatch.elapsedMilliseconds;
    if (!mounted) return;

    if (widget.detailed) {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) =>
              ReportPreviewScreen(photoPath: file.path, data: widget.data),
        ),
      );
      return;
    }

    var fix = _sensors.fresh();
    if (fix == null) {
      try {
        fix = await const LocationService().captureSnapshot();
      } on LocationServiceException catch (e) {
        if (mounted) _snack(e.message);
        return;
      }
    }

    // Non-blocking blur check: the default answer keeps the photo.
    if (looksBlurry(await sharpness(file.path)) && mounted) {
      final retake = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Photo floue'),
          content: const Text(
            'La photo semble floue. Voulez-vous la reprendre ?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('Reprendre'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('Garder'),
            ),
          ],
        ),
      );
      if (retake == true) return;
    }

    final id = const Uuid().v4();
    final draft = ReportDraft(
      deviceReportId: id,
      lat: fix.lat,
      lon: fix.lon,
      gpsAccuracyM: fix.gpsAccuracyM,
      speedKmh: fix.speedKmh,
      directionDeg: fix.directionDeg,
      capturedAt: fix.capturedAt,
      source: ReportSource.manual,
    );
    final photoPath = await keepPhoto(file.path, id);
    _timings['queued_ms'] = _stopwatch.elapsedMilliseconds;
    if (!mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    var cancelled = false;
    messenger.showSnackBar(
      SnackBar(
        duration: _undoWindow,
        persist: false, // snackbars with an action otherwise stay until tapped
        content: const Text('Signalement enregistré · envoi dans 5 s'),
        action: SnackBarAction(
          label: 'ANNULER',
          textColor: sabeelAmber,
          onPressed: () => cancelled = true,
        ),
      ),
    );
    Navigator.of(context).pop();
    await Future<void>.delayed(_undoWindow);
    if (cancelled) {
      messenger.showSnackBar(
        const SnackBar(content: Text('Signalement annulé.')),
      );
      return;
    }
    final stored = await widget.data.submit(
      QueuedReport(
        draft: draft,
        photoPath: photoPath,
        queuedAt: DateTime.now().toUtc(),
      ),
    );
    _timings['server_ack_ms'] = _stopwatch.elapsedMilliseconds;
    debugPrint('[Sabeel] capture timings (ms since camera open): $_timings');
    if (stored == null) return;
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          stored.notDetected
              ? 'Aucun nid-de-poule détecté : ouvrez « Mes Rapports » pour choisir.'
              : stored.isUploaded
              ? 'Envoyé · ${stored.reference}'
              : 'Hors ligne : envoi automatique dès le retour du réseau.',
        ),
        persist: false,
        action: stored.notDetected
            ? SnackBarAction(
                label: 'VOIR',
                onPressed: () => navigatorKey.currentState?.push(
                  MaterialPageRoute(
                    builder: (_) => ReportResultScreen(
                      data: widget.data,
                      reportId: stored.id,
                    ),
                  ),
                ),
              )
            : null,
      ),
    );
  }

  // -------------------------------------------------------------- driving

  Future<void> _startDriving() async {
    await WakelockPlus.enable();
    await _tts.setLanguage('fr-FR');
    _frameTimer = Timer.periodic(_frameEvery, (_) => _scoreFrame());
    _aheadSub = _sensors.updates.listen(_checkAhead);
  }

  Future<void> _scoreFrame() async {
    final controller = _controller;
    final fix = _sensors.fresh(maxAge: const Duration(seconds: 3));
    if (_scoring ||
        controller == null ||
        !controller.value.isInitialized ||
        controller.value.isTakingPicture) {
      return;
    }
    if (fix == null) return setState(() => _drivingStatus = 'Recherche GPS…');
    if (!shouldCapture(fix.speedKmh)) {
      _detector.reset();
      return setState(
        () => _drivingStatus = fix.speedKmh < 5
            ? 'En pause (véhicule à l’arrêt)'
            : 'En pause (> 80 km/h)',
      );
    }
    _scoring = true;
    try {
      final frame = await controller.takePicture();
      final jpeg = await shrinkForDetection(frame.path);
      if (jpeg == null) return;
      final result = await widget.data.api.detect(jpeg);
      _framesScored++;
      final confirmed = _detector.add(result.detected);
      setState(
        () => _drivingStatus = result.detected
            ? 'Nid-de-poule ? ${_detector.streak}/3'
            : 'Détection active',
      );
      if (confirmed) {
        HapticFeedback.heavyImpact();
        final id = const Uuid().v4();
        final draft = ReportDraft(
          deviceReportId: id,
          lat: fix.lat,
          lon: fix.lon,
          gpsAccuracyM: fix.gpsAccuracyM,
          speedKmh: fix.speedKmh,
          directionDeg: fix.directionDeg,
          capturedAt: fix.capturedAt,
          source: ReportSource.drivingMode,
        );
        final path = await keepPhoto(frame.path, id);
        unawaited(
          widget.data.submit(
            QueuedReport(
              draft: draft,
              photoPath: path,
              queuedAt: DateTime.now().toUtc(),
            ),
          ),
        );
        setState(() {
          _autoReports++;
          _drivingStatus = 'Nid-de-poule signalé automatiquement';
        });
        _detector.reset();
      }
    } catch (e) {
      setState(() => _drivingStatus = 'Hors ligne : détection en pause');
    } finally {
      _scoring = false;
    }
  }

  /// "Attention, nid-de-poule dans 150 mètres" for known potholes ahead.
  void _checkAhead(LocationSnapshot fix) {
    // Keep known potholes loaded around the car (~5 km box, reloaded every 2 km).
    final last = _loadedAround;
    if (last == null || distanceM(last.$1, last.$2, fix.lat, fix.lon) > 2000) {
      _loadedAround = (fix.lat, fix.lon);
      const d = 0.045;
      unawaited(
        widget.data.loadMap(
          bbox: '${fix.lon - d},${fix.lat - d},${fix.lon + d},${fix.lat + d}',
          state: 'open',
        ),
      );
    }
    if (fix.speedKmh < 10) return;
    for (final p in widget.data.potholes) {
      if (!p.isOpen ||
          (p.severity ?? 0) < 3 ||
          _announced.contains(p.potholeId)) {
        continue;
      }
      final ahead = isAhead(
        lat: fix.lat,
        lon: fix.lon,
        headingDeg: fix.directionDeg,
        targetLat: p.lat,
        targetLon: p.lon,
      );
      if (!ahead) continue;
      _announced.add(p.potholeId);
      final d = (distanceM(fix.lat, fix.lon, p.lat, p.lon) / 10).round() * 10;
      HapticFeedback.vibrate();
      _tts.speak('Attention, nid-de-poule dans $d mètres');
      setState(() => _drivingStatus = '⚠ Nid-de-poule à $d m');
      break;
    }
  }

  void _snack(String text) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  // ----------------------------------------------------------------- UI

  @override
  Widget build(BuildContext context) {
    if (widget.drivingMode) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Stack(
          fit: StackFit.expand,
          children: [
            _buildBody(),
            SafeArea(
              child: _DrivingOverlay(
                status: _drivingStatus,
                frames: _framesScored,
                reports: _autoReports,
                warning: _sensorError,
              ),
            ),
          ],
        ),
      );
    }
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(
          widget.detailed
              ? 'Signaler (mode détaillé)'
              : 'Signaler un nid-de-poule',
        ),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    final errorMessage = _errorMessage;
    if (errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.white, size: 48),
              const SizedBox(height: 12),
              Text(
                errorMessage,
                style: const TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  setState(() => _errorMessage = null);
                  _setupCamera();
                },
                child: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      );
    }
    final initializeFuture = _initializeControllerFuture;
    if (initializeFuture == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return FutureBuilder<void>(
      future: initializeFuture,
      builder: (context, snapshot) {
        final controller = _controller;
        if (snapshot.connectionState != ConnectionState.done ||
            controller == null ||
            !controller.value.isInitialized) {
          return const Center(child: CircularProgressIndicator());
        }
        if (widget.drivingMode) return Center(child: CameraPreview(controller));
        return Stack(
          fit: StackFit.expand,
          children: [
            Center(child: CameraPreview(controller)),
            const _GuidanceOverlay(),
            if (_sensorError != null)
              Positioned(
                top: 12,
                left: 12,
                right: 12,
                child: _Banner(text: _sensorError!, color: sabeelAmber),
              ),
            Positioned(
              bottom: 32,
              left: 0,
              right: 0,
              child: Center(
                child: Semantics(
                  button: true,
                  label: 'Prendre la photo',
                  child: GestureDetector(
                    onTap: _capture,
                    child: Container(
                      width: 84,
                      height: 84,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white,
                        border: Border.all(color: Colors.white54, width: 5),
                      ),
                      child: const Icon(
                        Icons.camera_alt,
                        color: Colors.black,
                        size: 36,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

/// Global navigator, so a snackbar action can open a screen after the camera closed.
final navigatorKey = GlobalKey<NavigatorState>();

class _Banner extends StatelessWidget {
  const _Banner({required this.text, required this.color});
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(12),
    ),
    child: Text(
      text,
      style: const TextStyle(color: sabeelInk, fontWeight: FontWeight.w600),
    ),
  );
}

/// Framing guide and rotating tips (high contrast for sunlight).
class _GuidanceOverlay extends StatefulWidget {
  const _GuidanceOverlay();

  @override
  State<_GuidanceOverlay> createState() => _GuidanceOverlayState();
}

class _GuidanceOverlayState extends State<_GuidanceOverlay> {
  static const _tips = [
    'Approchez-vous du nid-de-poule',
    'Gardez le téléphone stable',
    'Cadrez le trou entier avec son bord',
    'Incluez un peu de route autour',
  ];
  int _tip = 0;
  late final Timer _timer = Timer.periodic(
    const Duration(seconds: 3),
    (_) => setState(() => _tip = (_tip + 1) % _tips.length),
  );

  @override
  void initState() {
    super.initState();
    _timer;
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
    child: Column(
      children: [
        const Spacer(),
        Container(
          width: 260,
          height: 200,
          decoration: BoxDecoration(
            border: Border.all(color: sabeelAmber, width: 3),
            borderRadius: BorderRadius.circular(18),
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: Colors.black87,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            _tips[_tip],
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const Spacer(flex: 2),
      ],
    ),
  );
}

/// Dashcam chrome over the live view: live dot, elapsed time, status, counters, stop.
class _DrivingOverlay extends StatefulWidget {
  const _DrivingOverlay({
    required this.status,
    required this.frames,
    required this.reports,
    this.warning,
  });

  final String status;
  final int frames;
  final int reports;
  final String? warning;

  @override
  State<_DrivingOverlay> createState() => _DrivingOverlayState();
}

class _DrivingOverlayState extends State<_DrivingOverlay>
    with SingleTickerProviderStateMixin {
  final _clock = Stopwatch()..start();
  late final Timer _tick = Timer.periodic(
    const Duration(seconds: 1),
    (_) => setState(() {}),
  );
  late final _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat(reverse: true);

  @override
  void initState() {
    super.initState();
    _tick;
  }

  @override
  void dispose() {
    _tick.cancel();
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final e = _clock.elapsed;
    final time =
        '${e.inMinutes.toString().padLeft(2, '0')}:${(e.inSeconds % 60).toString().padLeft(2, '0')}';
    const chip = BoxDecoration(
      color: Color(0x99000000),
      borderRadius: BorderRadius.all(Radius.circular(20)),
    );
    const label = TextStyle(
      color: Colors.white,
      fontWeight: FontWeight.w600,
      fontFeatures: [FontFeature.tabularFigures()],
    );
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                decoration: chip,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FadeTransition(
                      opacity: _pulse,
                      child: const Icon(
                        Icons.circle,
                        color: Color(0xFFE5484D),
                        size: 12,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text('EN DIRECT  $time', style: label),
                  ],
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                decoration: chip,
                child: Text('${widget.reports} signalé(s)', style: label),
              ),
            ],
          ),
          if (widget.warning != null) ...[
            const SizedBox(height: 12),
            _Banner(text: widget.warning!, color: sabeelAmber),
          ],
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: chip,
            child: Text(
              widget.status,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '${widget.frames} images analysées · aucune image vide n’est conservée',
            style: const TextStyle(color: Colors.white70, fontSize: 12),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: 72,
            height: 72,
            child: ElevatedButton(
              onPressed: () => Navigator.of(context).pop(),
              style: ElevatedButton.styleFrom(
                shape: const CircleBorder(),
                backgroundColor: Colors.white,
                foregroundColor: const Color(0xFFE5484D),
                padding: EdgeInsets.zero,
              ),
              child: const Icon(Icons.stop_rounded, size: 40),
            ),
          ),
          const SizedBox(height: 8),
          const Text('Arrêter', style: label),
        ],
      ),
    );
  }
}
