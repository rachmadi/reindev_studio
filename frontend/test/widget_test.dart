import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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

    // 8. Verifikasi Eksekusi Deploy dengan Prompt Terisi (REQ-022)
    await tester.tap(deployBtnFinder);
    await tester.pump(); // Frame awal saat loading aktif
    expect(find.text('Deploying Squad...'), findsOneWidget);

    // Selesaikan timer simulasi deploy agar tidak ada pending timer
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
  });
}

