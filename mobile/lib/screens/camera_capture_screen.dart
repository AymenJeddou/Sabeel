import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../services/offline_queue_repository.dart';
import 'report_preview_screen.dart';

/// The camera screen: a live in-app preview with a shutter button.
///
/// [drivingMode] turns it into a dashcam-style live view (live indicator,
/// elapsed time, stop button). It's UI only for now: nothing is recorded
/// or analysed yet.
class CameraCaptureScreen extends StatefulWidget {
  const CameraCaptureScreen({
    super.key,
    required this.queueRepository,
    this.drivingMode = false,
  });

  final OfflineQueueRepository queueRepository;
  final bool drivingMode;

  @override
  State<CameraCaptureScreen> createState() => _CameraCaptureScreenState();
}

class _CameraCaptureScreenState extends State<CameraCaptureScreen>
    with WidgetsBindingObserver {
  CameraController? _controller;
  Future<void>? _initializeControllerFuture;
  String? _errorMessage;
  bool _isSettingUp = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _setupCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  /// Tears the camera down only when the app is genuinely backgrounded.
  /// The permission dialog only makes the app `inactive`, and releasing the
  /// controller there leaves the preview stuck on a spinner once the dialog
  /// is dismissed.
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

      final backCamera = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        backCamera,
        ResolutionPreset.high,
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
      if (!mounted) return;
      setState(() {});
    } on CameraException catch (e) {
      if (!mounted) return;
      setState(() => _errorMessage = _messageForCameraException(e));
    } finally {
      _isSettingUp = false;
    }
  }

  void _retry() {
    setState(() => _errorMessage = null);
    _setupCamera();
  }

  String _messageForCameraException(CameraException e) {
    switch (e.code) {
      case 'CameraAccessDenied':
      case 'CameraAccessDeniedWithoutPrompt':
      case 'CameraAccessRestricted':
        return 'Permission caméra refusée. Active-la dans les réglages du '
            'téléphone.';
      default:
        return "Impossible d'ouvrir la caméra (${e.code}).";
    }
  }

  Future<void> _capture() async {
    final controller = _controller;
    if (controller == null ||
        !controller.value.isInitialized ||
        controller.value.isTakingPicture) {
      return;
    }
    try {
      final file = await controller.takePicture();
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ReportPreviewScreen(
            photoPath: file.path,
            queueRepository: widget.queueRepository,
          ),
        ),
      );
    } on CameraException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Erreur de capture (${e.code}).')));
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.drivingMode) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Stack(
          fit: StackFit.expand,
          children: [
            _buildBody(),
            const SafeArea(child: _DrivingOverlay()),
          ],
        ),
      );
    }
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text('Signaler un nid-de-poule'),
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
              ElevatedButton(onPressed: _retry, child: const Text('Réessayer')),
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
            Positioned(
              bottom: 32,
              left: 0,
              right: 0,
              child: Center(
                child: GestureDetector(
                  onTap: _capture,
                  child: Container(
                    width: 76,
                    height: 76,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Colors.white,
                      border: Border.all(color: Colors.white54, width: 4),
                    ),
                    child: const Icon(
                      Icons.camera_alt,
                      color: Colors.black,
                      size: 32,
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

/// Dashcam chrome over the live view: pulsing "EN DIRECT" dot, elapsed
/// time, a status line and a stop button.
class _DrivingOverlay extends StatefulWidget {
  const _DrivingOverlay();

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
        '${e.inMinutes.toString().padLeft(2, '0')}:'
        '${(e.inSeconds % 60).toString().padLeft(2, '0')}';
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
                child: const Text('Mode conduite', style: label),
              ),
            ],
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: chip,
            child: const Text(
              'Détection automatique — bientôt disponible',
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
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
