import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:reindev_studio/main.dart';

void main() {
  testWidgets('Iterasi 4 — Mission Control Hub, Presets, Engine Selector & Tuning Test', (WidgetTester tester) async {
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

    // 1. Verifikasi Header Studio Branding & Theme Toggle
    expect(find.text('ReinDev Studio'), findsOneWidget);
    expect(find.text('Autonomous Multi-Agent Software Engineering'), findsOneWidget);

    // 2. Verifikasi Mission Control Hub (REQ-019)
    expect(find.text('Mission Control Hub'), findsOneWidget);
    expect(find.text('MISSION INTENT'), findsOneWidget);
    expect(find.text('PRESET MISI CEPAT'), findsOneWidget);

    // 3. Verifikasi Input Form & Validasi Kosong (REQ-019)
    final deployBtnFinder = find.widgetWithText(FilledButton, 'Deploy Autonomous Squad');
    expect(deployBtnFinder, findsOneWidget);

    // Klik deploy saat prompt kosong -> Harus memunculkan pesan error
    await tester.tap(deployBtnFinder);
    await tester.pumpAndSettle();
    expect(find.text('Deskripsi misi tidak boleh kosong.'), findsOneWidget);

    // 4. Verifikasi Preset Misi Cepat & Tombol Clear 'x' (REQ-022, REQ-019)
    final fastApiPreset = find.widgetWithText(ActionChip, 'FastAPI CRUD');
    expect(fastApiPreset, findsOneWidget);
    await tester.tap(fastApiPreset);
    await tester.pumpAndSettle();

    // Pesan error harus hilang dan field terisi
    expect(find.text('Deskripsi misi tidak boleh kosong.'), findsNothing);
    expect(
      find.textContaining('Bangun modul REST API FastAPI'),
      findsOneWidget,
    );

    // Verifikasi keberadaan tombol 'x' untuk menghapus teks prompt (REQ-019 / TC-IA-03)
    final clearBtnFinder = find.byIcon(Icons.close_rounded);
    expect(clearBtnFinder, findsWidgets);

    // Klik tombol 'x' pada suffixIcon
    await tester.tap(clearBtnFinder.first);
    await tester.pumpAndSettle();

    // Verifikasi teks kembali kosong
    expect(find.textContaining('Bangun modul REST API FastAPI'), findsNothing);

    // Terapkan preset kembali untuk pengujian selanjutnya
    await tester.tap(fastApiPreset);
    await tester.pumpAndSettle();

    // 5. Verifikasi Engine Selector Dropdown & Chip Penjelas Performa (REQ-020 / TC-IA-04)
    expect(find.text('AI ENGINE SPECIFICATION'), findsOneWidget);
    expect(find.text('LOCAL RESIDENT'), findsOneWidget);
    expect(find.text('Ollama (qwen2.5-coder:7b)'), findsWidgets);
    expect(
      find.textContaining('Fast • Resident 6GB (Offline Bebas Biaya)'),
      findsOneWidget,
    );

    // Scroll sedikit ke bawah untuk memastikan Tuning section terlihat jelas
    await tester.drag(find.byType(ListView).first, const Offset(0, -200));
    await tester.pumpAndSettle();

    // 6. Verifikasi Squad Tuning Slider & Language Selector (REQ-021)
    expect(find.text('SQUAD TUNING'), findsOneWidget);
    expect(find.text('Max QA Loops (Self-Healing):'), findsOneWidget);
    expect(find.text('3x'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'Python'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'Dart / Flutter'), findsOneWidget);

    // Ganti target bahasa ke Dart
    final dartChip = find.widgetWithText(ChoiceChip, 'Dart / Flutter');
    await tester.tap(dartChip);
    await tester.pumpAndSettle();

    // 7. Verifikasi 4 Tab Workspace & 5 Topologi Kartu Agen (REQ-018)
    expect(find.text('Agent Squad Timeline'), findsOneWidget);
    expect(find.text('Product Manager'), findsOneWidget);
    expect(find.text('System Architect'), findsOneWidget);
    expect(find.text('Developer'), findsOneWidget);
    expect(find.text('QA Tester'), findsOneWidget);
    expect(find.text('Code Reviewer'), findsOneWidget);

    // 8. Verifikasi Eksekusi Deploy dengan Prompt Terisi & Live Pipeline (REQ-022, REQ-023 s.d. REQ-026)
    await tester.tap(deployBtnFinder);
    await tester.pump(); // Frame awal saat loading aktif
    expect(find.text('Deploying Squad...'), findsOneWidget);

    // Verifikasi Thought Stream Container & Header (REQ-025)
    expect(find.text('Live Agent Thought & Collaboration Stream'), findsOneWidget);

    // Majukan waktu ke fase PM
    await tester.pump(const Duration(milliseconds: 1500));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.textContaining('User Stories & SMART Specifications'), findsOneWidget);

    // Selesaikan seluruh siklus simulasi pipeline (8.5 detik)
    await tester.pump(const Duration(seconds: 10));
    await tester.pumpAndSettle();

    // Verifikasi seluruh event tuntas dan tombol kembali ke status siap
    expect(find.text('Deploy Autonomous Squad'), findsOneWidget);
  });

  testWidgets('Iterasi 5 — Agent Pipeline Visualization, Thought Stream & Filter (REQ-023 s.d. REQ-026)', (WidgetTester tester) async {
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

    // 1. Verifikasi 5 Agent Cards dalam kondisi awal 'Ready' (REQ-023)
    expect(find.text('AUTONOMOUS AGENT SQUAD TOPOLOGY'), findsOneWidget);
    expect(find.text('Product Manager'), findsOneWidget);
    expect(find.text('System Architect'), findsOneWidget);
    expect(find.text('Developer'), findsOneWidget);
    expect(find.text('QA Tester'), findsOneWidget);
    expect(find.text('Code Reviewer'), findsOneWidget);
    expect(find.text('Ready'), findsWidgets);

    // 2. Verifikasi Empty State Thought Stream (REQ-025)
    expect(find.text('Live Agent Thought & Collaboration Stream'), findsOneWidget);
    expect(find.text('Belum ada aliran pemikiran agen.'), findsOneWidget);
    expect(
      find.textContaining("Ketik deskripsi fitur di panel kiri dan klik 'Deploy Autonomous Squad'"),
      findsOneWidget,
    );

    // 3. Verifikasi Filter Chips (REQ-025)
    expect(find.widgetWithText(ChoiceChip, 'All Events (0)'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'Product Manager (0)'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'System Architect (0)'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'Developer (0)'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'QA Tester (0)'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'Code Reviewer (0)'), findsOneWidget);

    // 4. Pilih Preset & Deploy Autonomous Squad
    final fastApiPreset = find.widgetWithText(ActionChip, 'FastAPI CRUD');
    await tester.tap(fastApiPreset);
    await tester.pumpAndSettle();

    final deployBtnFinder = find.widgetWithText(FilledButton, 'Deploy Autonomous Squad');
    await tester.tap(deployBtnFinder);
    await tester.pump();

    // 5. Verifikasi Auto-switch ke Tab 0 & Thought Stream Mulai Terisi
    expect(find.text('Deploying Squad...'), findsOneWidget);
    expect(find.text('Belum ada aliran pemikiran agen.'), findsNothing);
    expect(find.text('Squad Mission Deployment Initiated'), findsOneWidget);

    // 6. Majukan ke fase PM (REQ-023, REQ-025)
    await tester.pump(const Duration(milliseconds: 1500));
    expect(find.textContaining('User Stories & SMART Specifications'), findsOneWidget);

    // 7. Selesaikan seluruh siklus simulasi hingga selesai (REQ-026)
    await tester.pump(const Duration(seconds: 10));
    await tester.pumpAndSettle();

    // 8. Verifikasi Seluruh Status Kartu Agen Selesai & MarkdownBody Rendered (REQ-023, REQ-025, REQ-026)
    expect(find.textContaining('Completed'), findsWidgets);
    expect(find.byType(MarkdownBody), findsWidgets);
    expect(find.text('Deploy Autonomous Squad'), findsOneWidget);
  });

  testWidgets('Iterasi 5 — Multi-Language Dynamic Code Synthesis & Runner (Dart / Flutter Stack Test)', (WidgetTester tester) async {
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

    // 1. Pilih Preset 'Flutter Widget'
    final flutterPreset = find.widgetWithText(ActionChip, 'Flutter Widget');
    expect(flutterPreset, findsOneWidget);
    await tester.tap(flutterPreset);
    await tester.pumpAndSettle();

    // 2. Verifikasi Auto-alignment target language ke 'Dart / Flutter'
    expect(find.textContaining('Bangun komponen widget kartu metrik modern'), findsOneWidget);

    // 3. Deploy Misi Flutter
    final deployBtnFinder = find.widgetWithText(FilledButton, 'Deploy Autonomous Squad');
    await tester.tap(deployBtnFinder);
    await tester.pump();

    // 4. Majukan waktu hingga siklus selesai
    await tester.pump(const Duration(seconds: 10));
    await tester.pumpAndSettle();

    // 5. Verifikasi bahwa yang dihasilkan adalah kode Dart/Flutter (Bukan Python)
    expect(find.textContaining('Flutter / Dart Test Runner'), findsOneWidget);
    expect(find.textContaining('lib/widgets/metric_card_widget.dart'), findsWidgets);
    expect(find.byType(MarkdownBody), findsWidgets);
    expect(find.text('Deploy Autonomous Squad'), findsOneWidget);
  });
}


