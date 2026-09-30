import 'package:flutter/material.dart';

import '../services/sabeel_data.dart';
import 'home_screen.dart';
import 'map_screen.dart';
import 'reports_screen.dart';

/// The 3-tab shell from the design (mobile/design/main.png,map.png,reports.png):
/// Accueil / Carte / Mes signalements.
class RootShell extends StatefulWidget {
  const RootShell({super.key, required this.data});

  final SabeelData data;

  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    widget.data.refresh();
  }

  void _goToTab(int index) {
    if (index != _selectedIndex) widget.data.refresh();
    setState(() => _selectedIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeScreen(data: widget.data, onNavigateToTab: _goToTab),
      MapScreen(data: widget.data),
      ReportsScreen(data: widget.data),
    ];

    return Scaffold(
      body: SafeArea(
        child: IndexedStack(index: _selectedIndex, children: pages),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _goToTab,
        height: 66,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Accueil',
          ),
          NavigationDestination(
            icon: Icon(Icons.map_outlined),
            selectedIcon: Icon(Icons.map),
            label: 'Carte',
          ),
          NavigationDestination(
            icon: Icon(Icons.list_alt_outlined),
            selectedIcon: Icon(Icons.list_alt),
            label: 'Mes Rapports',
          ),
        ],
      ),
    );
  }
}
