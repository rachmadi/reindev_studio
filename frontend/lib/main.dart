import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'providers/app_providers.dart';
import 'theme/app_theme.dart';
import 'views/studio_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const ProviderScope(
      child: ReinDevStudioApp(),
    ),
  );
}

class ReinDevStudioApp extends ConsumerWidget {
  const ReinDevStudioApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);

    return MaterialApp(
      title: "ReinDev Studio — Autonomous Multi-Agent Software Engineering",
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme(),
      darkTheme: AppTheme.darkTheme(),
      themeMode: themeMode,
      home: const StudioScreen(),
    );
  }
}