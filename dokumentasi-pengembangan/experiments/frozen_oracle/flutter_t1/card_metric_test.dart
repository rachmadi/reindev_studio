import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../lib/card_metric.dart';

void main() {
  testWidgets('renders CardMetric with Material 3 Card and Riverpod state', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: ThemeData(useMaterial3: true),
          home: Scaffold(
            body: CardMetric(
              data: MetricData(title: 'Revenue', value: '1000', color: Colors.blue),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(CardMetric), findsOneWidget);
    expect(find.byType(Card), findsOneWidget);
    expect(find.text('Revenue'), findsOneWidget);
    expect(find.text('1000'), findsOneWidget);
  });

  testWidgets('renders responsively inside constrained box without overflow', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: ThemeData(useMaterial3: true),
          home: Scaffold(
            body: SizedBox(
              width: 300,
              height: 200,
              child: CardMetric(
                data: MetricData(title: 'CPU Usage', value: '78%', color: Colors.green),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(CardMetric), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
