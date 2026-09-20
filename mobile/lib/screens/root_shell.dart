import 'package:flutter/material.dart';

import '../services/offline_queue_repository.dart';
import 'home_screen.dart';
import 'map_screen.dart';
import 'reports_screen.dart';

/// The 3-tab shell from the design (mobile/design/main.png,map.png,reports.png):
/// Accueil / Carte / Mes signalements.
class RootShell extends StatefulWidget {
  const RootShell({super.key, required this.queueRepository});

  final OfflineQueueRepository queueRepository;

  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  int _selectedIndex = 0;

  void _goToTab(int index) {
    setState(() => _selectedIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeScreen(
        queueRepository: widget.queueRepository,
        onNavigateToTab: _goToTab,
      ),
      MapScreen(queueRepository: widget.queueRepository),
      ReportsScreen(queueRepository: widget.queueRepository),
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
