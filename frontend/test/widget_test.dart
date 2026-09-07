import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:reindev_studio/main.dart';

void main() {
  testWidgets('Iterasi 3 — Studio Screen Shell, MD3 Header, & 3-Panel Layout Test', (WidgetTester tester) async {
    // Atur ukuran surface desktop simulasi (1400 x 900)
    await tester.binding.setSurfaceSize(const Size(1400, 900));
    addTearDown(() async {
      await tester.binding.setSurfaceSize(null);
    });

    await tester.pumpWidget(
      const ProviderScope(
        child: ReinDevStudioApp(),
      ),
    );
    await tester.pumpAndSettle();

    // 1. Verifikasi Header Studio Branding
    expect(find.text('ReinDev Studio'), findsOneWidget);
    expect(find.text('v1.0-IIDD'), findsOneWidget);
    expect(find.text('Autonomous Multi-Agent Software Engineering'), findsOneWidget);

    // 2. Verifikasi Engine & Backend Status Badge
    expect(find.text('Ollama (qwen2.5-coder:7b)'), findsOneWidget);
    expect(find.text('FastAPI ws://127.0.0.1:8000'), findsOneWidget);

    // 3. Verifikasi Left Control Hub Panel (REQ-017)
    expect(find.text('Mission Control Hub'), findsOneWidget);
    expect(find.text('MISSION INTENT'), findsOneWidget);
    expect(find.text('PRESET MISI CEPAT'), findsOneWidget);
    expect(find.text('Deploy Autonomous Squad'), findsOneWidget);

    // 4. Verifikasi Workspace Tabs (REQ-017)
    expect(find.text('Agent Squad Timeline'), findsOneWidget);
    expect(find.text('Code Canvas & Explorer'), findsOneWidget);
    expect(find.text('Sandbox Terminal'), findsOneWidget);
    expect(find.text('Quality & Review Report'), findsOneWidget);

    // 5. Verifikasi 5 Agent Squad Topology Cards
    expect(find.text('Product Manager'), findsOneWidget);
    expect(find.text('System Architect'), findsOneWidget);
    expect(find.text('Developer'), findsOneWidget);
    expect(find.text('QA Tester'), findsOneWidget);
    expect(find.text('Code Reviewer'), findsOneWidget);

    // 6. Verifikasi Tombol Toggle Theme (REQ-018)
    final themeToggleFinder = find.byType(IconButton);
    expect(themeToggleFinder, findsOneWidget);
    await tester.tap(themeToggleFinder);
    await tester.pumpAndSettle();
  });
}