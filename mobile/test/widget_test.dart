import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:roadscan_mobile/app/roadscan_app.dart';
import 'package:roadscan_mobile/services/offline_queue_repository.dart';

void main() {
  testWidgets('RoadScan app boots into the Accueil tab', (
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final queueRepository = OfflineQueueRepository(prefs);
    await queueRepository.load();

    await tester.pumpWidget(RoadScanApp(queueRepository: queueRepository));
    await tester.pumpAndSettle();

    expect(find.text('RoadScan'), findsOneWidget);
    expect(find.text('Signaler un nid-de-poule'), findsOneWidget);
  });
}
