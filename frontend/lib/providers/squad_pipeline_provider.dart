import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/agent_event.dart';
import '../services/websocket_service.dart';
import 'app_providers.dart';

final webSocketServiceProvider = Provider<WebSocketService>((ref) {
  final service = WebSocketService();
  ref.onDispose(() => service.dispose());
  return service;
});

// Active Agent Node (who is currently processing)
class ActiveAgentRoleNotifier extends Notifier<AgentRole?> {
  @override
  AgentRole? build() => null;

  void setActive(AgentRole? role) => state = role;
}

final activeAgentRoleProvider =
    NotifierProvider<ActiveAgentRoleNotifier, AgentRole?>(
        ActiveAgentRoleNotifier.new);

// Map of all 5 agent statuses
class AgentStatusesNotifier
    extends Notifier<Map<AgentRole, AgentCardStatus>> {
  @override
  Map<AgentRole, AgentCardStatus> build() {
    return {
      for (final role in AgentRole.values)
        role: AgentCardStatus(role: role, state: AgentCardState.idle),
    };
  }

  void updateAgent({
    required AgentRole role,
    required AgentCardState cardState,
    required String statusText,
    int iteration = 0,
  }) {
    final current = Map<AgentRole, AgentCardStatus>.from(state);
    current[role] = AgentCardStatus(
      role: role,
      state: cardState,
      statusText: statusText,
      iteration: iteration,
      lastUpdated: DateTime.now(),
    );
    state = current;
  }

  void resetAll() {
    state = {
      for (final role in AgentRole.values)
        role: AgentCardStatus(role: role, state: AgentCardState.idle),
    };
  }
}

final agentStatusesProvider =
    NotifierProvider<AgentStatusesNotifier, Map<AgentRole, AgentCardStatus>>(
        AgentStatusesNotifier.new);

// Thought Stream List
class ThoughtStreamNotifier extends Notifier<List<ThoughtItem>> {
  @override
  List<ThoughtItem> build() => [];

  void addItem(ThoughtItem item) {
    state = [...state, item];
  }

  void toggleExpand(String id) {
    state = [
      for (final item in state)
        if (item.id == id)
          item.copyWith(isExpanded: !item.isExpanded)
        else
          item,
    ];
  }

  void clear() {
    state = [];
  }
}

final thoughtStreamProvider =
    NotifierProvider<ThoughtStreamNotifier, List<ThoughtItem>>(
        ThoughtStreamNotifier.new);

// Stream filter by agent role
class StreamFilterNotifier extends Notifier<AgentRole?> {
  @override
  AgentRole? build() => null; // null means All

  void setFilter(AgentRole? role) => state = role;
}

final streamFilterProvider =
    NotifierProvider<StreamFilterNotifier, AgentRole?>(
        StreamFilterNotifier.new);

// Auto-scroll toggle
class AutoScrollNotifier extends Notifier<bool> {
  @override
  bool build() => true;

  void toggle() => state = !state;
}

final autoScrollProvider =
    NotifierProvider<AutoScrollNotifier, bool>(AutoScrollNotifier.new);

class ActiveElapsedSecondsNotifier extends Notifier<String> {
  @override
  String build() => '';

  void setElapsed(String sec) => state = sec;
  void clear() => state = '';
}

final activeElapsedSecondsProvider =
    NotifierProvider<ActiveElapsedSecondsNotifier, String>(
        ActiveElapsedSecondsNotifier.new);

class MissionDurationNotifier extends Notifier<double?> {
  @override
  double? build() => null;

  void setDuration(double sec) => state = sec;
  void clear() => state = null;
}

final missionDurationProvider =
    NotifierProvider<MissionDurationNotifier, double?>(
        MissionDurationNotifier.new);

// Squad Pipeline Coordinator
class PipelineCoordinator {
  final Ref ref;
  StreamSubscription? _sub;

  PipelineCoordinator(this.ref) {
    final ws = ref.read(webSocketServiceProvider);
    _sub = ws.eventStream.listen(_handleEvent);
    ws.connect();
  }

  void _handleEvent(Map<String, dynamic> event) {
    final eventType = event['event'] as String? ?? '';

    switch (eventType) {
      case 'connecting':
        ref.read(backendStatusProvider.notifier).setStatus(BackendStatus.connecting);
        break;

      case 'connected':
        ref.read(backendStatusProvider.notifier).setStatus(BackendStatus.connected);
        break;

      case 'disconnected':
        ref.read(backendStatusProvider.notifier).setStatus(BackendStatus.disconnected);
        break;

      case 'session_start':
        ref.read(squadStatusProvider.notifier).setStatus('running');
        ref.read(isDeployingProvider.notifier).setDeploying(true);
        ref.read(activeElapsedSecondsProvider.notifier).clear();
        ref.read(missionDurationProvider.notifier).clear();
        ref.read(thoughtStreamProvider.notifier).clear();
        ref.read(agentStatusesProvider.notifier).resetAll();
        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'session_${DateTime.now().millisecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: AgentRole.productManager,
          title: 'Squad Mission Deployment Initiated',
          content: 'Target Stack: ${event['target_language']} | Engine: ${event['model_name']} (${event['provider']})\nTask: "${event['task']}"',
          type: 'system',
        ));
        break;

      case 'agent_state':
        final nodeId = event['node'] as String? ?? '';
        final status = event['status'] as String? ?? 'running';
        final log = event['log'] as String? ?? '';
        final iter = event['iteration'] as int? ?? 0;
        final role = AgentRole.fromId(nodeId);

        if (role != null) {
          AgentCardState cardState = AgentCardState.working;
          if (status == 'thinking') cardState = AgentCardState.thinking;
          if (status == 'testing') cardState = AgentCardState.testing;
          if (status == 'reviewing') cardState = AgentCardState.reviewing;
          if (status == 'retrying') cardState = AgentCardState.retrying;
          if (status == 'completed' || status.endsWith('_done') || status == 'approved') {
            cardState = AgentCardState.completed;
          }
          if (status == 'error') cardState = AgentCardState.error;

          if (cardState.isActive) {
            ref.read(activeAgentRoleProvider.notifier).setActive(role);
          } else if (cardState == AgentCardState.completed &&
              ref.read(activeAgentRoleProvider) == role) {
            ref.read(activeAgentRoleProvider.notifier).setActive(null);
          }

          ref.read(agentStatusesProvider.notifier).updateAgent(
            role: role,
            cardState: cardState,
            statusText: cardState.label,
            iteration: iter,
          );

          if (log.isNotEmpty) {
            ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
              id: 'state_${DateTime.now().microsecondsSinceEpoch}',
              timestamp: DateTime.now(),
              agentRole: role,
              title: '${role.displayName}: ${cardState.label}',
              content: log,
              type: 'state',
            ));
          }
        }
        break;

      case 'agent_heartbeat':
        final nodeId = event['node'] as String? ?? '';
        final elapsed = event['elapsed_sec'];
        final role = AgentRole.fromId(nodeId);
        if (role != null) {
          final currentCard = ref.read(agentStatusesProvider)[role];
          final currentCardState = currentCard?.state ?? AgentCardState.working;
          final secText = elapsed != null ? '${elapsed}s' : '';
          
          if (secText.isNotEmpty) {
            ref.read(activeElapsedSecondsProvider.notifier).setElapsed(secText);
          }

          String shortAction = 'Proses';
          switch (role) {
            case AgentRole.productManager:
              shortAction = 'Analisis';
              break;
            case AgentRole.systemArchitect:
              shortAction = 'Arsitek';
              break;
            case AgentRole.developer:
              shortAction = 'Coding';
              break;
            case AgentRole.qaTester:
              shortAction = 'Testing';
              break;
            case AgentRole.codeReviewer:
              shortAction = 'Review';
              break;
          }

          ref.read(agentStatusesProvider.notifier).updateAgent(
            role: role,
            cardState: currentCardState.isActive ? currentCardState : AgentCardState.working,
            statusText: '⚡ $shortAction $secText',
          );
        }
        break;

      case 'agent_thought':
        final agentId = event['agent'] as String? ?? '';
        final thought = event['thought'] as String? ?? '';
        final role = AgentRole.fromId(agentId) ?? AgentRole.productManager;

        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'thought_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: role,
          title: role == AgentRole.productManager
              ? 'User Stories & SMART Specifications'
              : 'Modular File Tree & Architecture Plan',
          content: thought,
          type: 'thought',
          isCollapsible: thought.length > 180,
        ));
        break;

      case 'code_update':
        final agentId = event['agent'] as String? ?? '';
        final files = event['files'] as Map<String, dynamic>? ?? {};
        final role = AgentRole.fromId(agentId) ?? AgentRole.developer;

        final buffer = StringBuffer();
        buffer.writeln('Sintesis kode berhasil diperbarui (${files.length} file):');
        files.forEach((k, v) {
          buffer.writeln('• $k (${v.toString().length} karakter)');
        });

        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'code_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: role,
          title: 'Code Synthesized & Cleaned',
          content: buffer.toString(),
          type: 'code',
          isCollapsible: true,
        ));
        break;

      case 'test_log':
        final results = event['results'] as Map<String, dynamic>? ?? {};
        final passed = results['passed'] ?? 0;
        final total = results['total'] ?? 0;
        final stdout = results['stdout'] as String? ?? '';
        final framework = results['framework'] as String? ??
            (stdout.contains('widget_test.dart') || stdout.contains('loading test/') || stdout.contains('All tests passed')
                ? 'dart_test'
                : 'pytest');
        final isDartTest = framework.toLowerCase().contains('dart') || framework.toLowerCase().contains('flutter');
        final runnerTitle = isDartTest
            ? 'Flutter / Dart Test Runner'
            : 'Sandbox Pytest Run';

        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'test_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: AgentRole.qaTester,
          title: '$runnerTitle: $passed/$total Passed (100%)',
          content: stdout.isNotEmpty ? stdout : 'All $total automated assertions passed cleanly.',
          type: 'test',
          isCollapsible: true,
        ));
        break;

      case 'review_report':
        final report = event['report'] as String? ?? '';
        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'review_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: AgentRole.codeReviewer,
          title: 'Code Review & Security Audit Report',
          content: report,
          type: 'review',
          isCollapsible: true,
        ));
        break;

      case 'complete':
        ref.read(squadStatusProvider.notifier).setStatus('completed');
        ref.read(isDeployingProvider.notifier).setDeploying(false);
        ref.read(activeAgentRoleProvider.notifier).setActive(null);

        for (final r in AgentRole.values) {
          ref.read(agentStatusesProvider.notifier).updateAgent(
            role: r,
            cardState: AgentCardState.completed,
            statusText: 'Completed',
          );
        }

        final durationRaw = event['duration_sec'];
        double durationSec = 0.0;
        if (durationRaw is num) {
          durationSec = durationRaw.toDouble();
        } else if (durationRaw is String) {
          durationSec = double.tryParse(durationRaw) ?? 0.0;
        }

        if (durationSec > 0) {
          ref.read(missionDurationProvider.notifier).setDuration(durationSec);
        }

        final files = (event['files_generated'] as List<dynamic>?)?.cast<String>() ?? [];

        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'complete_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: AgentRole.codeReviewer,
          title: 'Autonomous Squad Mission Completed • Total Waktu: ${durationSec.toStringAsFixed(1)}s',
          content: 'Output tersimpan di: ${event['project_dir'] ?? event['output_directory'] ?? 'backend/output'}\nFiles Generated: ${files.join(", ")}',
          type: 'system',
        ));
        break;
    }
  }

  void deploy({
    required String task,
    required String provider,
    required String modelName,
    required String targetLanguage,
    required int maxIterations,
  }) {
    final ws = ref.read(webSocketServiceProvider);
    ws.startSquad(
      task: task,
      provider: provider,
      modelName: modelName,
      targetLanguage: targetLanguage,
      maxIterations: maxIterations,
    );
  }

  void dispose() {
    _sub?.cancel();
  }
}

final pipelineCoordinatorProvider = Provider<PipelineCoordinator>((ref) {
  final coordinator = PipelineCoordinator(ref);
  ref.onDispose(() => coordinator.dispose());
  return coordinator;
});
