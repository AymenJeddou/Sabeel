import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:roadscan_mobile/app/roadscan_app.dart';
import 'package:roadscan_mobile/services/offline_queue_repository.dart';
import 'package:roadscan_mobile/services/sabeel_data.dart';

import 'helpers/offline_api.dart';

void main() {
  testWidgets('app plays the splash then lands on the Accueil tab', (
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final queueRepository = OfflineQueueRepository(prefs);
    await queueRepository.load();

    await tester.pumpWidget(
      RoadScanApp(data: SabeelData(queueRepository, api: const OfflineApi())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Sabeel'), findsOneWidget);
    expect(find.text('Signaler un nid-de-poule'), findsOneWidget);
  });
}
