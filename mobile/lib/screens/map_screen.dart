import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../app/brand.dart';
import '../services/offline_queue_repository.dart';

/// The Carte tab (mobile/design/map.png): OpenStreetMap tiles with a pin per
/// report held on this device.
///
/// Markers are all drawn in the "non évalué" colour because severity comes
/// from WP1's model via WP3's API, which this sprint doesn't call yet — the
/// severity legend documents the scheme those colours will use.
class MapScreen extends StatefulWidget {
  const MapScreen({super.key, required this.queueRepository});

  final OfflineQueueRepository queueRepository;

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  static const _tunisCenter = LatLng(36.8065, 10.1815);
  static const _minZoom = 3.0;
  static const _maxZoom = 18.0;

  final MapController _mapController = MapController();

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }

  void _zoomBy(double delta) {
    final camera = _mapController.camera;
    _mapController.move(
      camera.center,
      (camera.zoom + delta).clamp(_minZoom, _maxZoom),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.queueRepository,
      builder: (context, _) {
        final reports = widget.queueRepository.queue;
        final initialCenter = reports.isEmpty
            ? _tunisCenter
            : LatLng(reports.first.draft.lat, reports.first.draft.lon);

        return Stack(
          children: [
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: initialCenter,
                initialZoom: 13,
                minZoom: _minZoom,
                maxZoom: _maxZoom,
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.roadscan.roadscan_mobile',
                ),
                MarkerLayer(
                  markers: [
                    for (final report in reports)
                      Marker(
                        point: LatLng(report.draft.lat, report.draft.lon),
                        width: 22,
                        height: 22,
                        child: const _ReportMarker(),
                      ),
                  ],
                ),
              ],
            ),
            const Positioned(top: 12, left: 12, child: _LegendCard()),
            Positioned(
              top: 12,
              right: 12,
              child: Column(
                children: [
                  _MapButton(icon: Icons.add, onTap: () => _zoomBy(1)),
                  const SizedBox(height: 8),
                  _MapButton(icon: Icons.remove, onTap: () => _zoomBy(-1)),
                ],
              ),
            ),
            const Positioned(bottom: 6, right: 8, child: _Attribution()),
          ],
        );
      },
    );
  }
}

class _ReportMarker extends StatelessWidget {
  const _ReportMarker();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: sabeelNavy,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 3),
        boxShadow: const [
          BoxShadow(
            color: Color(0x40000000),
            blurRadius: 5,
            offset: Offset(0, 2),
          ),
        ],
      ),
    );
  }
}

/// Required by the OpenStreetMap tile usage policy.
class _Attribution extends StatelessWidget {
  const _Attribution();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.white70,
        borderRadius: BorderRadius.circular(4),
      ),
      child: const Text(
        '© OpenStreetMap',
        style: TextStyle(fontSize: 10, color: Colors.black87),
      ),
    );
  }
}

class _LegendCard extends StatelessWidget {
  const _LegendCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: sabeelLine),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'SÉVÉRITÉ',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: sabeelMuted,
            ),
          ),
          SizedBox(height: 6),
          _LegendRow(color: Color(0xFF2E9E4B), label: 'Mineur'),
          SizedBox(height: 4),
          _LegendRow(color: Color(0xFFE8862E), label: 'Modéré'),
          SizedBox(height: 4),
          _LegendRow(color: Color(0xFFD93B3B), label: 'Urgent'),
          SizedBox(height: 4),
          _LegendRow(color: sabeelNavy, label: 'Non évalué'),
        ],
      ),
    );
  }
}

class _LegendRow extends StatelessWidget {
  const _LegendRow({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
        ),
      ],
    );
  }
}

class _MapButton extends StatelessWidget {
  const _MapButton({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      shape: const CircleBorder(),
      elevation: 2,
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Icon(icon, size: 20),
        ),
      ),
    );
  }
}
