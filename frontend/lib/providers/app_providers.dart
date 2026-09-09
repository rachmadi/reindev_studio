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
  BackendStatus build() => BackendStatus.connecting;

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

class PromptInputNotifier extends Notifier<String> {
  @override
  String build() => "";

  void setPrompt(String prompt) => state = prompt;
  void clear() => state = "";
}

final promptInputProvider =
    NotifierProvider<PromptInputNotifier, String>(PromptInputNotifier.new);

class MaxQaLoopsNotifier extends Notifier<int> {
  @override
  int build() => 3;

  void setLoops(int loops) => state = loops;
}

final maxQaLoopsProvider =
    NotifierProvider<MaxQaLoopsNotifier, int>(MaxQaLoopsNotifier.new);

class TargetLanguageNotifier extends Notifier<String> {
  @override
  String build() => "Python";

  void setLanguage(String lang) => state = lang;
}

final targetLanguageProvider =
    NotifierProvider<TargetLanguageNotifier, String>(
        TargetLanguageNotifier.new);

class IsDeployingNotifier extends Notifier<bool> {
  @override
  bool build() => false;

  void setDeploying(bool deploying) => state = deploying;
}

final isDeployingProvider =
    NotifierProvider<IsDeployingNotifier, bool>(IsDeployingNotifier.new);

class ExecutorInterventionNotifier extends Notifier<bool> {
  @override
  bool build() => true;

  void setIntervention(bool enabled) {
    state = enabled;
    ref.read(executorModeProvider.notifier).state = enabled ? "ON" : "OFF";
  }

  void toggle() => setIntervention(!state);
}

final executorInterventionProvider =
    NotifierProvider<ExecutorInterventionNotifier, bool>(
        ExecutorInterventionNotifier.new);

class ExecutorModeNotifier extends Notifier<String> {
  @override
  String build() => "ON";

  void setMode(String mode) {
    final upper = mode.toUpperCase();
    state = upper;
    ref.read(executorInterventionProvider.notifier).state = (upper != "OFF");
  }
}

final executorModeProvider =
    NotifierProvider<ExecutorModeNotifier, String>(ExecutorModeNotifier.new);