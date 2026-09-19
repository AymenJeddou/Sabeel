import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import '../services/api_client.dart';
import '../services/location_service.dart';
import 'result_screen.dart';

class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  final _picker = ImagePicker();
  final _locationService = LocationService();
  final _apiClient = RoadScanApiClient();

  // One device_report_id for the life of the app session -- no offline
  // queue/persistence in this insurance build (see Sprint 1 plan §4).
  final String _deviceReportId = const Uuid().v4();

  File? _photo;
  bool _submitting = false;
  String? _error;

  Future<void> _pickPhoto(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (picked != null) {
      setState(() {
        _photo = File(picked.path);
        _error = null;
      });
    }
  }

  Future<void> _submit() async {
    if (_photo == null) {
      setState(() => _error = 'Take or pick a photo first.');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final location = await _locationService.getCurrentFix();
      final result = await _apiClient.submitReport(
        deviceReportId: _deviceReportId,
        location: location,
        photo: _photo!,
        source: 'manual',
      );

      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(builder: (_) => ResultScreen(result: result)));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('RoadScan — Report a pothole')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Expanded(
              child: Container(
                width: double.infinity,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade400),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: _photo == null
                    ? const Center(child: Text('No photo selected'))
                    : ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.file(_photo!, fit: BoxFit.cover),
                      ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _submitting ? null : () => _pickPhoto(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Camera'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _submitting ? null : () => _pickPhoto(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library),
                    label: const Text('Gallery'),
                  ),
                ),
              ],
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _submitting ? null : _submit,
                icon: _submitting
                    ? const SizedBox(
                        width: 16, height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Icon(Icons.send),
                label: Text(_submitting ? 'Submitting...' : 'Submit report'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
