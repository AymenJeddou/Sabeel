import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../app/brand.dart';
import '../models/remote_report.dart';
import '../services/api_client.dart';
import '../services/location_service.dart';
import '../services/rules.dart';
import '../services/sabeel_data.dart';
import '../widgets/status_tracker.dart';

/// The Carte tab (issue #32): the real, deduplicated potholes of the visible
/// area from GET /map (reloaded 400 ms after the map stops moving), clustered
/// so 5,000+ points stay smooth, severity / status filters, the last result
/// kept offline, and one-tap "I see it too" actions behind a 50 m geofence.
class MapScreen extends StatefulWidget {
  const MapScreen({super.key, required this.data});

  final SabeelData data;

  @override
  State<MapScreen> createState() => _MapScreenState();
}

enum _Filter { open, urgent, fixed }

class _MapScreenState extends State<MapScreen> {
  static const _tunisCenter = LatLng(36.8065, 10.1815);
  final MapController _mapController = MapController();
  Timer? _debounce;
  _Filter _filter = _Filter.open;
  double _zoom = 13;

  @override
  void dispose() {
    _debounce?.cancel();
    _mapController.dispose();
    super.dispose();
  }

  void _scheduleLoad() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), _load);
  }

  Future<void> _load() async {
    final b = _mapController.camera.visibleBounds;
    await widget.data.loadMap(
      bbox: '${b.west},${b.south},${b.east},${b.north}',
      state: _filter == _Filter.fixed ? 'fixed' : 'open',
      sev: _filter == _Filter.urgent ? '4,5' : null,
    );
  }

  void _setFilter(_Filter f) {
    setState(() => _filter = f);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.data,
      builder: (context, _) {
        final potholes = widget.data.potholes;
        final mine = {for (final r in widget.data.queue.queue) r.potholeId};
        final clusters = clusterIndices([
          for (final p in potholes) (p.lat, p.lon),
        ], _zoom);
        return Stack(
          children: [
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: _tunisCenter,
                initialZoom: 13,
                minZoom: 5,
                maxZoom: 19,
                onMapReady: _load,
                onPositionChanged: (camera, hasGesture) {
                  if (camera.zoom != _zoom) setState(() => _zoom = camera.zoom);
                  _scheduleLoad();
                },
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.roadscan.roadscan_mobile',
                ),
                MarkerLayer(
                  markers: [
                    for (final c in clusters)
                      if (c.length == 1)
                        _potholeMarker(
                          potholes[c.first],
                          mine.contains(potholes[c.first].potholeId),
                        )
                      else
                        _clusterMarker([for (final i in c) potholes[i]]),
                  ],
                ),
                const RichAttributionWidget(
                  attributions: [TextSourceAttribution('OpenStreetMap')],
                ),
              ],
            ),
            Positioned(
              top: 12,
              left: 12,
              right: 12,
              child: Row(
                children: [
                  for (final (f, label) in [
                    (_Filter.open, 'Ouverts'),
                    (_Filter.urgent, 'Urgents'),
                    (_Filter.fixed, 'Réparés'),
                  ]) ...[
                    ChoiceChip(
                      label: Text(label),
                      selected: _filter == f,
                      onSelected: (_) => _setFilter(f),
                      selectedColor: sabeelNavy,
                      labelStyle: TextStyle(
                        color: _filter == f ? Colors.white : sabeelInk,
                      ),
                      showCheckmark: false,
                    ),
                    const SizedBox(width: 8),
                  ],
                  const Spacer(),
                  if (widget.data.mapOffline)
                    const Chip(
                      label: Text('données hors ligne'),
                      backgroundColor: Color(0xFFFBF1DE),
                    ),
                ],
              ),
            ),
            const Positioned(left: 12, bottom: 12, child: _Legend()),
          ],
        );
      },
    );
  }

  Marker _potholeMarker(MapPothole p, bool isMine) {
    final color = p.status == 'fixed' ? Colors.grey : severityColor(p.severity);
    return Marker(
      point: LatLng(p.lat, p.lon),
      width: 30,
      height: 30,
      child: GestureDetector(
        onTap: () => showPotholeSheet(context, widget.data, p),
        child: Semantics(
          button: true,
          label: 'Nid-de-poule ${p.ref}, sévérité ${p.severity ?? 'inconnue'}',
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color,
              border: Border.all(
                color: isMine ? sabeelNavy : Colors.white,
                width: isMine ? 4 : 2.5,
              ),
              boxShadow: const [
                BoxShadow(color: Colors.black26, blurRadius: 4),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Marker _clusterMarker(List<MapPothole> group) {
    final worst = group
        .map((p) => p.severity ?? 0)
        .reduce((a, b) => a > b ? a : b);
    final lat = group.map((p) => p.lat).reduce((a, b) => a + b) / group.length;
    final lon = group.map((p) => p.lon).reduce((a, b) => a + b) / group.length;
    final size = 34.0 + (group.length.clamp(2, 200) / 200) * 24;
    return Marker(
      point: LatLng(lat, lon),
      width: size,
      height: size,
      child: GestureDetector(
        onTap: () => _mapController.move(LatLng(lat, lon), _zoom + 2),
        child: Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: severityColor(
              worst == 0 ? null : worst,
            ).withValues(alpha: 0.9),
            border: Border.all(color: Colors.white, width: 3),
          ),
          child: Text(
            '${group.length}',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final (s, label) in [
          (5, '5'),
          (4, '4'),
          (3, '3'),
          (1, '1–2'),
        ]) ...[
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: severityColor(s),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 4),
          Text(label, style: const TextStyle(fontSize: 12)),
          const SizedBox(width: 10),
        ],
        const Text(
          '◉ les vôtres',
          style: TextStyle(fontSize: 12, color: sabeelNavy),
        ),
      ],
    ),
  );
}

/// Bottom sheet for one pothole: details, tracker, and the citizen actions.
void showPotholeSheet(BuildContext context, SabeelData data, MapPothole p) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    backgroundColor: Colors.white,
    builder: (_) => SafeArea(
      child: _PotholeSheet(data: data, pothole: p),
    ),
  );
}

class _PotholeSheet extends StatefulWidget {
  const _PotholeSheet({required this.data, required this.pothole});

  final SabeelData data;
  final MapPothole pothole;

  @override
  State<_PotholeSheet> createState() => _PotholeSheetState();
}

class _PotholeSheetState extends State<_PotholeSheet> {
  static const _doneKey = 'confirmations_sent';
  String? _blocked = 'Localisation…';
  LocationSnapshot? _fix;
  bool _busy = false;
  String? _message;
  Set<String> _done = {};

  @override
  void initState() {
    super.initState();
    _locate();
    SharedPreferences.getInstance().then(
      (p) => setState(() => _done = (p.getStringList(_doneKey) ?? []).toSet()),
    );
  }

  Future<void> _locate() async {
    try {
      final fix = await const LocationService().captureSnapshot();
      final p = widget.pothole;
      if (!mounted) return;
      setState(() {
        _fix = fix;
        _blocked = geofenceReason(
          distanceM(fix.lat, fix.lon, p.lat, p.lon),
          fix.gpsAccuracyM,
        );
      });
    } on LocationServiceException catch (e) {
      if (mounted) setState(() => _blocked = e.message);
    }
  }

  Future<void> _send(String kind) async {
    final fix = _fix;
    if (fix == null) return;
    setState(() => _busy = true);
    try {
      final r = await widget.data.api.confirm(
        potholeId: widget.pothole.potholeId,
        kind: kind,
        lat: fix.lat,
        lon: fix.lon,
        accuracyM: fix.gpsAccuracyM,
      );
      final prefs = await SharedPreferences.getInstance();
      _done.add('${widget.pothole.potholeId}:$kind');
      await prefs.setStringList(_doneKey, _done.toList());
      setState(
        () => _message = r.created
            ? 'Merci ! ${r.status == 'confirmed' ? 'Le nid-de-poule est maintenant confirmé.' : 'Votre retour est enregistré.'}'
            : 'Déjà confirmé depuis ce téléphone.',
      );
    } on ApiClientException catch (e) {
      setState(
        () => _message = switch (e.statusCode) {
          403 => e.message,
          409 => 'Action impossible dans l’état actuel du nid-de-poule.',
          429 => 'Trop de confirmations aujourd’hui, réessayez demain.',
          _ => e.message,
        },
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.pothole;
    final days = DateTime.now().difference(p.createdOn).inDays;
    final actions = p.status == 'fixed'
        ? [
            ('not_fixed', 'Toujours là', Icons.report_outlined),
            ('fixed_ok', 'Bien réparé', Icons.thumb_up_alt_outlined),
          ]
        : [('seen', 'Je le vois aussi', Icons.visibility_outlined)];
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            p.addressLabel ??
                '${p.lat.toStringAsFixed(5)}, ${p.lon.toStringAsFixed(5)}',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(
            [
              p.ref,
              p.severity == null
                  ? 'Sévérité à évaluer'
                  : 'Sévérité ${p.severity}/5',
              '${p.reportCount} signalement${p.reportCount > 1 ? 's' : ''}',
              '${p.confirmCount} « je le vois aussi »',
              days == 0 ? 'aujourd’hui' : 'il y a $days j',
            ].join(' · '),
            style: const TextStyle(color: sabeelMuted),
          ),
          const SizedBox(height: 16),
          StatusTracker(status: p.status),
          const SizedBox(height: 16),
          for (final (kind, label, icon) in actions) ...[
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed:
                    _busy ||
                        _blocked != null ||
                        _done.contains('${p.potholeId}:$kind')
                    ? null
                    : () => _send(kind),
                icon: Icon(icon),
                label: Text(
                  _done.contains('${p.potholeId}:$kind')
                      ? 'Déjà confirmé'
                      : label,
                ),
              ),
            ),
            const SizedBox(height: 8),
          ],
          TextButton.icon(
            onPressed:
                _busy ||
                    _blocked != null ||
                    _done.contains('${p.potholeId}:not_pothole')
                ? null
                : () => _send('not_pothole'),
            icon: const Icon(Icons.block, size: 18),
            label: const Text('Pas un nid-de-poule'),
          ),
          if (_blocked != null)
            Text(
              _blocked!,
              style: const TextStyle(color: sabeelMuted, fontSize: 12),
            ),
          if (_message != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                _message!,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
        ],
      ),
    );
  }
}
