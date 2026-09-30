import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../app/brand.dart';
import '../config.dart';
import '../models/remote_report.dart';
import '../services/sabeel_data.dart';

/// The Carte tab (mobile/design/map.png): every known pothole in the city
/// from the Core API, coloured by severity, plus this phone's reports still
/// waiting to upload (navy). Tap a pin for its photo and status.
class MapScreen extends StatefulWidget {
  const MapScreen({super.key, required this.data});

  final SabeelData data;

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  static const _tunisCenter = LatLng(36.8065, 10.1815);
  static const _minZoom = 3.0;
  static const _maxZoom = 18.0;

  final MapController _mapController = MapController();
  bool _showFixed = false;

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
      listenable: widget.data,
      builder: (context, _) {
        final reports = widget.data.queue.queue;
        final potholes =
            widget.data.potholes
                .where((p) => p.isOpen || (_showFixed && p.status == 'fixed'))
                .toList()
              // Most severe drawn last, i.e. on top.
              ..sort((a, b) => (a.score ?? 0).compareTo(b.score ?? 0));
        const initialCenter = _tunisCenter;

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
                    for (final p in potholes)
                      Marker(
                        point: LatLng(p.lat, p.lon),
                        width: 18.0 + p.clusterSize.clamp(1, 5) * 3,
                        height: 18.0 + p.clusterSize.clamp(1, 5) * 3,
                        child: GestureDetector(
                          onTap: () => showPotholeSheet(context, p),
                          child: _ReportMarker(
                            color: p.status == 'fixed'
                                ? sabeelTeal
                                : severityColor(p.score),
                          ),
                        ),
                      ),
                    for (final report in reports)
                      Marker(
                        point: LatLng(report.draft.lat, report.draft.lon),
                        width: 22,
                        height: 22,
                        child: const _ReportMarker(color: sabeelNavy),
                      ),
                  ],
                ),
              ],
            ),
            const Positioned(top: 12, left: 12, child: _LegendCard()),
            Positioned(
              bottom: 16,
              left: 12,
              child: FilterChip(
                label: Text(
                  '${potholes.length} nids-de-poule · afficher réparés',
                  style: const TextStyle(fontSize: 12),
                ),
                selected: _showFixed,
                onSelected: (v) => setState(() => _showFixed = v),
                backgroundColor: Colors.white,
                selectedColor: sabeelTeal.withValues(alpha: 0.15),
                side: const BorderSide(color: sabeelLine),
              ),
            ),
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
  const _ReportMarker({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: color,
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
          _LegendRow(color: Color(0xFFC8322B), label: 'Urgent (5)'),
          SizedBox(height: 4),
          _LegendRow(color: Color(0xFFE36A1B), label: 'Grave (4)'),
          SizedBox(height: 4),
          _LegendRow(color: Color(0xFFE0A21A), label: 'Modéré (3)'),
          SizedBox(height: 4),
          _LegendRow(color: Color(0xFF3E9E6B), label: 'Mineur (1-2)'),
          SizedBox(height: 4),
          _LegendRow(color: Color(0xFF8A8F98), label: 'À évaluer'),
          SizedBox(height: 4),
          _LegendRow(color: sabeelNavy, label: "En attente d'envoi"),
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

/// Photo, place and progress of one pothole (map pins and "Mes Rapports").
void showPotholeSheet(BuildContext context, RemoteReport p) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    backgroundColor: Colors.white,
    builder: (context) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (p.photoUrl != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.network(
                  '$apiBaseUrl${p.photoUrl}',
                  height: 170,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (_, _, _) => const SizedBox.shrink(),
                ),
              ),
            const SizedBox(height: 14),
            Text(
              p.address ??
                  '${p.lat.toStringAsFixed(5)}, ${p.lon.toStringAsFixed(5)}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              [
                p.ref,
                p.score == null
                    ? 'Sévérité à évaluer'
                    : 'Sévérité ${p.score}/5',
                '${p.clusterSize} signalement${p.clusterSize > 1 ? 's' : ''}',
              ].join(' · '),
              style: const TextStyle(color: sabeelMuted),
            ),
            const SizedBox(height: 16),
            StatusTracker(status: p.status),
          ],
        ),
      ),
    ),
  );
}

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
    final reached = _steps.indexOf(status);
    final color = statusColors[status] ?? sabeelNavy;
    return Row(
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
                  fontWeight: i == reached ? FontWeight.w700 : FontWeight.w500,
                  color: i <= reached ? sabeelInk : sabeelMuted,
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
