import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum BackendStatus { connected, connecting, disconnected }

class ThemeModeNotifier extends Notifier<ThemeMode> {
  @override
  ThemeMode build() => ThemeMode.dark;

  void setTheme(ThemeMode mode) => state = mode;
  void toggle() {
    state = state == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
  }
}

final themeModeProvider =
    NotifierProvider<ThemeModeNotifier, ThemeMode>(ThemeModeNotifier.new);

class BackendStatusNotifier extends Notifier<BackendStatus> {
  @override
  BackendStatus build() => BackendStatus.connected;

  void setStatus(BackendStatus status) => state = status;
}

final backendStatusProvider =
    NotifierProvider<BackendStatusNotifier, BackendStatus>(
        BackendStatusNotifier.new);

class ActiveWorkspaceTabNotifier extends Notifier<int> {
  @override
  int build() => 0;

  void setTab(int index) => state = index;
}

final activeWorkspaceTabProvider =
    NotifierProvider<ActiveWorkspaceTabNotifier, int>(
        ActiveWorkspaceTabNotifier.new);

class ActiveEngineNotifier extends Notifier<String> {
  @override
  String build() => "Ollama (qwen2.5-coder:7b)";

  void setEngine(String engine) => state = engine;
}

final activeEngineProvider =
    NotifierProvider<ActiveEngineNotifier, String>(ActiveEngineNotifier.new);

class SquadStatusNotifier extends Notifier<String> {
  @override
  String build() => "idle";

  void setStatus(String status) => state = status;
}

final squadStatusProvider =
    NotifierProvider<SquadStatusNotifier, String>(SquadStatusNotifier.new);