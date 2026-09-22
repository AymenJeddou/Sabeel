import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:roadscan_mobile/screens/root_shell.dart';
import 'package:roadscan_mobile/services/offline_queue_repository.dart';

Future<OfflineQueueRepository> _buildRepository() async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  final repository = OfflineQueueRepository(prefs);
  await repository.load();
  return repository;
}

void main() {
  testWidgets('shows exactly 3 bottom navigation destinations', (tester) async {
    final repository = await _buildRepository();

    await tester.pumpWidget(
      MaterialApp(home: RootShell(queueRepository: repository)),
    );
    await tester.pumpAndSettle();

    expect(find.byType(NavigationDestination), findsNWidgets(3));
  });

  testWidgets('tapping a destination updates the selected tab', (tester) async {
    final repository = await _buildRepository();

    await tester.pumpWidget(
      MaterialApp(home: RootShell(queueRepository: repository)),
    );
    await tester.pumpAndSettle();

    NavigationBar navBar() =>
        tester.widget<NavigationBar>(find.byType(NavigationBar));

    expect(navBar().selectedIndex, 0);

    // Icons.map_outlined also appears in the Home screen's "Carte" shortcut
    // card (which stays mounted under IndexedStack), so the tap must be
    // scoped to the NavigationBar to hit the destination, not the card.
    final mapDestination = find.descendant(
      of: find.byType(NavigationBar),
      matching: find.byIcon(Icons.map_outlined),
    );
    await tester.tap(mapDestination);
    await tester.pumpAndSettle();

    expect(navBar().selectedIndex, 1);
  });
}
