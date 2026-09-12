import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/agent_event.dart';
import '../services/websocket_service.dart';
import 'app_providers.dart';

// ===========================================================================
// Iterasi 6 — State Models
// ===========================================================================

/// Terminal line classification for coloring
enum TerminalLineType { pass, fail, warning, info, header, prompt, normal }

/// Single terminal log line
class TerminalEntry {
  final String text;
  final TerminalLineType type;
  final DateTime timestamp;

  const TerminalEntry({
    required this.text,
    required this.type,
    required this.timestamp,
  });

  /// Classify a raw output line into a TerminalLineType
  factory TerminalEntry.fromRaw(String raw) {
    final stripped = _stripAnsi(raw);
    TerminalLineType type;

    final lower = stripped.toLowerCase();
    if (lower.contains(' passed') ||
        lower.contains('all tests passed') ||
        lower.contains('ok') && lower.startsWith('test ') ||
        lower.contains(': pass') ||
        lower.contains('✓') ||
        lower.contains('+ ') && lower.contains('test')) {
      type = TerminalLineType.pass;
    } else if (lower.contains('failed') ||
        lower.contains('error') ||
        lower.contains('exception') ||
        lower.contains('✗') ||
        lower.contains('assertion failed') ||
        lower.contains('traceback')) {
      type = TerminalLineType.fail;
    } else if (lower.contains('warn') || lower.contains('deprecated')) {
      type = TerminalLineType.warning;
    } else if (stripped.startsWith('==') ||
        stripped.startsWith('--') ||
        stripped.startsWith('##') ||
        stripped.startsWith('Running ') ||
        stripped.startsWith('Dart ') ||
        stripped.startsWith('Flutter ')) {
      type = TerminalLineType.header;
    } else if (lower.contains('info') || lower.contains('collecting')) {
      type = TerminalLineType.info;
    } else if (stripped.startsWith('\$') || stripped.startsWith('>')) {
      type = TerminalLineType.prompt;
    } else {
      type = TerminalLineType.normal;
    }

    return TerminalEntry(
      text: stripped,
      type: type,
      timestamp: DateTime.now(),
    );
  }

  static String _stripAnsi(String input) {
    return input.replaceAll(RegExp(r'\x1B\[[0-9;]*[mGKHF]'), '');
  }
}

/// Diff line types
enum DiffLineType { added, removed, context, hunk }

/// Single line in a diff chunk
class DiffLine {
  final String content;
  final DiffLineType type;
  final int? lineNumber;

  const DiffLine({
    required this.content,
    required this.type,
    this.lineNumber,
  });
}

/// A complete file diff produced during a self-healing iteration
class DiffEntry {
  final String fileName;
  final int iteration;
  final List<DiffLine> lines;
  final DateTime timestamp;

  const DiffEntry({
    required this.fileName,
    required this.iteration,
    required this.lines,
    required this.timestamp,
  });

  factory DiffEntry.compute({
    required String fileName,
    required String oldContent,
    required String newContent,
    required int iteration,
  }) {
    final oldLines = oldContent.split('\n');
    final newLines = newContent.split('\n');
    final diffLines = _computeUnifiedDiff(oldLines, newLines);
    return DiffEntry(
      fileName: fileName,
      iteration: iteration,
      lines: diffLines,
      timestamp: DateTime.now(),
    );
  }

  static List<DiffLine> _computeUnifiedDiff(
    List<String> oldLines,
    List<String> newLines,
  ) {
    // Simple line-diff: mark added/removed by comparing old vs new
    final result = <DiffLine>[];
    final oldSet = oldLines.toSet();
    final newSet = newLines.toSet();

    result.add(const DiffLine(
      content: '@@ Self-Healing Revision @@',
      type: DiffLineType.hunk,
    ));

    int lineNum = 1;
    for (final line in oldLines) {
      if (!newSet.contains(line)) {
        result.add(DiffLine(
          content: line,
          type: DiffLineType.removed,
          lineNumber: lineNum,
        ));
      }
      lineNum++;
    }
    lineNum = 1;
    for (final line in newLines) {
      if (!oldSet.contains(line)) {
        result.add(DiffLine(
          content: line,
          type: DiffLineType.added,
          lineNumber: lineNum,
        ));
      }
      lineNum++;
    }

    return result;
  }
}

// ===========================================================================
// Iterasi 6 — Providers
// ===========================================================================

/// Map of filename -> file content received from code_update events
class CodeFilesNotifier extends Notifier<Map<String, String>> {
  @override
  Map<String, String> build() => {};

  void updateFiles(Map<String, String> newFiles) {
    final current = Map<String, String>.from(state);
    current.addAll(newFiles);
    state = current;
  }

  void clear() => state = {};
}

final codeFilesProvider =
    NotifierProvider<CodeFilesNotifier, Map<String, String>>(
        CodeFilesNotifier.new);

/// Currently selected file path in the file tree
class SelectedFileNotifier extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String? path) => state = path;
}

final selectedFileProvider =
    NotifierProvider<SelectedFileNotifier, String?>(SelectedFileNotifier.new);

/// Terminal log lines from test_log events
class TerminalLogsNotifier extends Notifier<List<TerminalEntry>> {
  @override
  List<TerminalEntry> build() => [];

  void addLines(List<String> rawLines) {
    final entries = rawLines
        .where((l) => l.trim().isNotEmpty)
        .map(TerminalEntry.fromRaw)
        .toList();
    state = [...state, ...entries];
  }

  void addEntry(TerminalEntry entry) {
    state = [...state, entry];
  }

  void clear() => state = [];
}

final terminalLogsProvider =
    NotifierProvider<TerminalLogsNotifier, List<TerminalEntry>>(
        TerminalLogsNotifier.new);

/// Diff entries for the revision viewer (from code_update when iteration > 0)
class DiffEntriesNotifier extends Notifier<List<DiffEntry>> {
  @override
  List<DiffEntry> build() => [];

  void addDiff(DiffEntry entry) {
    state = [...state, entry];
  }

  void clear() => state = [];
}

final diffEntriesProvider =
    NotifierProvider<DiffEntriesNotifier, List<DiffEntry>>(
        DiffEntriesNotifier.new);

/// Live test suite execution statistics for the Terminal Toolbar chips
class TerminalStatsState {
  final int passed;
  final int failed;
  final int total;
  final bool hasRun;

  const TerminalStatsState({
    this.passed = 0,
    this.failed = 0,
    this.total = 0,
    this.hasRun = false,
  });
}

class TerminalStatsNotifier extends Notifier<TerminalStatsState> {
  @override
  TerminalStatsState build() => const TerminalStatsState();

  void updateStats({required int passed, required int failed, required int total}) {
    state = TerminalStatsState(passed: passed, failed: failed, total: total, hasRun: true);
  }

  void clear() => state = const TerminalStatsState();
}

final terminalStatsProvider =
    NotifierProvider<TerminalStatsNotifier, TerminalStatsState>(
        TerminalStatsNotifier.new);

/// Live Self-Healing loop tracking
class LoopState {
  final int currentLoop;
  final int maxLoops;
  final String status; // 'idle', 'running', 'retrying', 'max_reached', 'passed', 'completed'
  final String message;

  const LoopState({
    this.currentLoop = 0,
    this.maxLoops = 3,
    this.status = 'idle',
    this.message = '',
  });

  bool get isRunning => status == 'running' || status == 'retrying';
  bool get isMaxReached => status == 'max_reached' || (currentLoop >= maxLoops && currentLoop > 0);
  bool get isPassed => status == 'passed';
}

class LoopStatusNotifier extends Notifier<LoopState> {
  @override
  LoopState build() => const LoopState();

  void updateLoop({
    required int currentLoop,
    required int maxLoops,
    required String status,
    String message = '',
  }) {
    state = LoopState(
      currentLoop: currentLoop,
      maxLoops: maxLoops,
      status: status,
      message: message,
    );
  }

  void reset({int maxLoops = 3}) {
    state = LoopState(maxLoops: maxLoops, status: 'running');
  }

  void clear() => state = const LoopState();
}

final loopStatusProvider =
    NotifierProvider<LoopStatusNotifier, LoopState>(
        LoopStatusNotifier.new);

/// Official Code Reviewer & Security Audit Report state for Tab 3
class ReviewReportState {
  final String report;
  final String status;
  final int iteration;
  final int maxIterations;
  final DateTime? timestamp;

  const ReviewReportState({
    this.report = '',
    this.status = '',
    this.iteration = 0,
    this.maxIterations = 3,
    this.timestamp,
  });

  bool get isEmpty => report.isEmpty;
  
  bool get isApproved {
    if (isEmpty) return false;
    // Tolak secara eksplisit jika terdapat tag [NEEDS_REVISION] atau status bukan approved
    if (report.contains('[NEEDS_REVISION]')) return false;
    if (status.toLowerCase().contains('needs_revision') ||
        status.toLowerCase().contains('rejected') ||
        status.toLowerCase().contains('tests_failed')) {
      return false;
    }
    return report.contains('[APPROVED]') ||
        status.toLowerCase().contains('approved');
  }

  bool get needsRevision => !isEmpty && !isApproved;
}

class ReviewReportNotifier extends Notifier<ReviewReportState> {
  @override
  ReviewReportState build() => const ReviewReportState();

  void setReport(String report, String status, {int iteration = 0, int maxIterations = 3}) {
    state = ReviewReportState(
      report: report,
      status: status,
      iteration: iteration,
      maxIterations: maxIterations,
      timestamp: DateTime.now(),
    );
  }

  void clear() => state = const ReviewReportState();
}

final reviewReportProvider =
    NotifierProvider<ReviewReportNotifier, ReviewReportState>(
        ReviewReportNotifier.new);

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
        // --- Iterasi 6 reset ---
        ref.read(codeFilesProvider.notifier).clear();
        ref.read(selectedFileProvider.notifier).select(null);
        ref.read(terminalLogsProvider.notifier).clear();
        ref.read(terminalStatsProvider.notifier).clear();
        ref.read(diffEntriesProvider.notifier).clear();
        ref.read(reviewReportProvider.notifier).clear();
        final maxLoops = (event['max_iterations'] as num?)?.toInt() ?? 3;
        ref.read(loopStatusProvider.notifier).reset(maxLoops: maxLoops);
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

          final loopBadge = iter > 0 ? ' (Loop $iter)' : '';
          ref.read(agentStatusesProvider.notifier).updateAgent(
            role: role,
            cardState: cardState,
            statusText: '${cardState.label}$loopBadge',
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

      case 'phase_validation':
        final phase = event['phase'] as String? ?? '';
        final boundary = event['boundary'] as String? ?? '';
        final verdict = event['verdict'] as String? ?? '';
        final repairCount = (event['repair_count'] as num?)?.toInt() ?? 0;
        final maxRepairs = (event['max_repairs'] as num?)?.toInt() ?? 2;

        AgentRole? targetRole;
        if (phase == 'PM') targetRole = AgentRole.productManager;
        if (phase == 'ARCHITECT') targetRole = AgentRole.systemArchitect;
        if (phase == 'DEVELOPER') targetRole = AgentRole.developer;
        if (phase == 'TEST_SUITE' || phase == 'EXECUTOR') targetRole = AgentRole.qaTester;
        if (phase == 'REVIEWER') targetRole = AgentRole.codeReviewer;

        if (targetRole != null) {
          if (verdict == 'PASS') {
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: targetRole,
              cardState: AgentCardState.completed,
              statusText: '$boundary PASS',
            );
          } else {
            final isTerminal = repairCount >= maxRepairs;
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: targetRole,
              cardState: isTerminal ? AgentCardState.error : AgentCardState.retrying,
              statusText: isTerminal
                  ? '$boundary FAILED'
                  : '$boundary Repair $repairCount/$maxRepairs',
            );
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
        final iter = event['iteration'] as int? ?? 0;

        // --- REQ-027/028: Populate file tree & code viewer ---
        final typedFiles = files.map((k, v) => MapEntry(k, v.toString()));
        if (typedFiles.isNotEmpty) {
          // Compute diffs vs current state when self-healing (iter > 0)
          if (iter > 0) {
            final currentFiles = ref.read(codeFilesProvider);
            for (final entry in typedFiles.entries) {
              final oldContent = currentFiles[entry.key] ?? '';
              if (oldContent.isNotEmpty && oldContent != entry.value) {
                ref.read(diffEntriesProvider.notifier).addDiff(
                  DiffEntry.compute(
                    fileName: entry.key,
                    oldContent: oldContent,
                    newContent: entry.value,
                    iteration: iter,
                  ),
                );
              }
            }
          }
          ref.read(codeFilesProvider.notifier).updateFiles(typedFiles);
          // Auto-select first file if nothing is selected yet
          if (ref.read(selectedFileProvider) == null) {
            ref.read(selectedFileProvider.notifier).select(typedFiles.keys.first);
          }
        }

        // --- ThoughtStream card (existing behaviour) ---
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
        final rawPassed = results['passed_count'] ?? results['passed'];
        final int passed = (rawPassed is bool)
            ? (rawPassed ? 1 : 0)
            : (rawPassed is num ? rawPassed.toInt() : 0);
        final int total = (results['total'] as num?)?.toInt() ??
            (passed > 0 ? passed : 1);
        final int failed = (results['failed_count'] as num?)?.toInt() ??
            (passed == 0 ? 1 : 0);
        final stdout = ((results['stdout'] ?? results['output'] ?? '') as String).trim();
        final isSuccess = results['passed'] == true || (passed > 0 && failed == 0);
        final framework = results['framework'] as String? ??
            (stdout.contains('widget_test.dart') || stdout.contains('loading test/') || stdout.contains('All tests passed')
                ? 'dart_test'
                : 'pytest');
        final isDartTest = framework.toLowerCase().contains('dart') || framework.toLowerCase().contains('flutter');
        final runnerTitle = isDartTest
            ? 'Flutter / Dart Test Runner'
            : 'Sandbox Pytest Run';

        // --- REQ-029: Populate Sandbox Terminal ---
        final statusBadge = isSuccess
            ? '$passed/$total Passed (100%)'
            : '$failed Failed / $total Total';
        ref.read(terminalStatsProvider.notifier).updateStats(
          passed: passed,
          failed: failed,
          total: total,
        );
        ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
          text: '=== $runnerTitle — $statusBadge ===',
          type: isSuccess ? TerminalLineType.header : TerminalLineType.fail,
          timestamp: DateTime.now(),
        ));
        if (stdout.isNotEmpty) {
          ref.read(terminalLogsProvider.notifier).addLines(
            stdout.split('\n'),
          );
        } else {
          ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
            text: isSuccess
                ? 'All $total automated assertions passed cleanly.'
                : 'Execution finished with exit code ${results['exit_code'] ?? 1}.',
            type: isSuccess ? TerminalLineType.pass : TerminalLineType.fail,
            timestamp: DateTime.now(),
          ));
        }

        final streamTitle = isSuccess
            ? '$runnerTitle: $passed/$total Passed (100%)'
            : '$runnerTitle: $failed Test Failed (Self-Healing Activated)';
        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'test_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: AgentRole.qaTester,
          title: streamTitle,
          content: stdout.isNotEmpty ? stdout : 'Execution result: $statusBadge',
          type: 'test',
          isCollapsible: true,
        ));
        break;

      case 'loop_status':
        final curLoop = (event['current_loop'] as num?)?.toInt() ?? 0;
        final maxLoops = (event['max_loops'] as num?)?.toInt() ?? 3;
        final status = event['status'] as String? ?? '';
        final msg = event['message'] as String? ?? '';

        ref.read(loopStatusProvider.notifier).updateLoop(
          currentLoop: curLoop,
          maxLoops: maxLoops,
          status: status,
          message: msg,
        );

        if (status == 'retrying') {
          ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
            id: 'loop_${DateTime.now().microsecondsSinceEpoch}',
            timestamp: DateTime.now(),
            agentRole: AgentRole.qaTester,
            title: '🔁 Self-Healing: Loop $curLoop/$maxLoops Berjalan',
            content: msg,
            type: 'state',
          ));
          ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
            text: '--- [Self-Healing Activated]: Loop $curLoop/$maxLoops dipicu. Mengalihkan perbaikan ke Developer ---',
            type: TerminalLineType.warning,
            timestamp: DateTime.now(),
          ));
        } else if (status == 'max_reached') {
          ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
            id: 'loop_${DateTime.now().microsecondsSinceEpoch}',
            timestamp: DateTime.now(),
            agentRole: AgentRole.qaTester,
            title: '🛑 Batas Maksimum Self-Healing Tercapai ($curLoop/$maxLoops Loop)',
            content: msg,
            type: 'state',
          ));
          ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
            text: '--- [Batas Maksimum Self-Healing Tercapai]: QA Tester mengalihkan tugas ke Code Reviewer dengan bukti pengujian aktual ---',
            type: TerminalLineType.fail,
            timestamp: DateTime.now(),
          ));
        } else if (status == 'passed') {
          ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
            id: 'loop_${DateTime.now().microsecondsSinceEpoch}',
            timestamp: DateTime.now(),
            agentRole: AgentRole.qaTester,
            title: '✅ Verifikasi Sandbox Lolos Bersih (Loop $curLoop/$maxLoops)',
            content: msg,
            type: 'state',
          ));
        }
        break;

      case 'review_report':
        final report = event['report'] as String? ?? '';
        final status = event['status'] as String? ?? 'completed';
        final iter = (event['iteration'] as num?)?.toInt() ?? ref.read(loopStatusProvider).currentLoop;
        final maxLoops = (event['max_iterations'] as num?)?.toInt() ?? ref.read(loopStatusProvider).maxLoops;
        ref.read(reviewReportProvider.notifier).setReport(report, status, iteration: iter, maxIterations: maxLoops);
        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'review_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: AgentRole.codeReviewer,
          title: 'Code Review & Security Audit Report (Loop $iter/$maxLoops)',
          content: report,
          type: 'review',
          isCollapsible: true,
        ));
        break;

      case 'complete':
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

        // Tentukan kelulusan obyektif dari event payload dan state lokal
        final testResults = event['test_results'] as Map<String, dynamic>? ?? {};
        final bool rawTestPassed = event['tests_passed'] == true || testResults['passed'] == true;
        final int failedCount = (testResults['failed_count'] as num?)?.toInt() ?? 0;
        final bool testsPassed = rawTestPassed && failedCount == 0;
        
        final reviewReport = ref.read(reviewReportProvider);
        final bool isReviewApproved = event['is_approved'] == true || reviewReport.isApproved;
        final bool isApprovedForRelease = testsPassed && isReviewApproved;

        final int finalIterations = (event['iterations'] as num?)?.toInt() ??
            ref.read(loopStatusProvider).currentLoop;
        final int maxLoops = (event['max_iterations'] as num?)?.toInt() ??
            ref.read(loopStatusProvider).maxLoops;

        ref.read(loopStatusProvider.notifier).updateLoop(
          currentLoop: finalIterations,
          maxLoops: maxLoops,
          status: 'completed',
          message: isApprovedForRelease ? 'Approved' : 'Needs Revision',
        );

        ref.read(squadStatusProvider.notifier).setStatus(isApprovedForRelease ? 'completed' : 'needs_revision');
        ref.read(isDeployingProvider.notifier).setDeploying(false);
        ref.read(activeAgentRoleProvider.notifier).setActive(null);

        final contractStatus = event['contract_status'] as String? ?? '';
        final currentCards = ref.read(agentStatusesProvider);

        if (isApprovedForRelease) {
          for (final r in AgentRole.values) {
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: r,
              cardState: AgentCardState.completed,
              statusText: 'Completed',
            );
          }
        } else {
          // Perbarui status kartu agen sesuai eksekusi aktual (mencegah false completed)
          if (contractStatus != 'FROZEN' &&
              currentCards[AgentRole.systemArchitect]?.state != AgentCardState.completed) {
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: AgentRole.systemArchitect,
              cardState: AgentCardState.error,
              statusText: 'Boundary V2 FAILED',
            );
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: AgentRole.developer,
              cardState: AgentCardState.idle,
              statusText: 'Unreached (Zero Leakage)',
            );
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: AgentRole.qaTester,
              cardState: AgentCardState.idle,
              statusText: 'Unreached (Zero Leakage)',
            );
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: AgentRole.codeReviewer,
              cardState: AgentCardState.idle,
              statusText: 'Halted',
            );
          } else {
            ref.read(agentStatusesProvider.notifier).updateAgent(
              role: AgentRole.codeReviewer,
              cardState: AgentCardState.retrying,
              statusText: 'Needs Revision',
            );
          }
        }

        final files = (event['files_generated'] as List<dynamic>?)?.cast<String>() ?? [];

        // Penutup resmi terminal — mencerminkan kondisi aktual (Approved vs Needs Revision)
        if (isApprovedForRelease) {
          ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
            text: '=== SQUAD MISSION COMPLETED (Total: ${durationSec.toStringAsFixed(1)}s) ===',
            type: TerminalLineType.header,
            timestamp: DateTime.now(),
          ));
          ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
            text: '✓ Aplikasi berhasil dikembangkan, diverifikasi di sandbox, dan disetujui untuk rilis.',
            type: TerminalLineType.pass,
            timestamp: DateTime.now(),
          ));
        } else {
          ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
            text: '=== SQUAD MISSION FINISHED (PERLU REVISI) (Total: ${durationSec.toStringAsFixed(1)}s) ===',
            type: TerminalLineType.fail,
            timestamp: DateTime.now(),
          ));
          ref.read(terminalLogsProvider.notifier).addEntry(TerminalEntry(
            text: !testsPassed
                ? '⚠ Pengujian sandbox melaporkan kegagalan assertion. Kode belum memenuhi standar rilis.'
                : '⚠ Hasil audit Code Reviewer menyatakan [NEEDS_REVISION]. Aplikasi belum disetujui untuk rilis.',
            type: TerminalLineType.warning,
            timestamp: DateTime.now(),
          ));
        }

        ref.read(thoughtStreamProvider.notifier).addItem(ThoughtItem(
          id: 'complete_${DateTime.now().microsecondsSinceEpoch}',
          timestamp: DateTime.now(),
          agentRole: AgentRole.codeReviewer,
          title: isApprovedForRelease
              ? 'Autonomous Squad Mission Completed • Disetujui Rilis (${durationSec.toStringAsFixed(1)}s)'
              : 'Autonomous Squad Mission Finished • Perlu Revisi [NEEDS_REVISION] (${durationSec.toStringAsFixed(1)}s)',
          content: isApprovedForRelease
              ? 'Output tersimpan di: ${event['project_dir'] ?? event['output_directory'] ?? 'backend/output'}\nFiles Generated: ${files.join(", ")}'
              : 'Hasil audit memerlukan perbaikan lebih lanjut sebelum rilis.\nStatus: NEEDS_REVISION | Test Passed: $testsPassed\nFiles: ${files.join(", ")}',
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
    bool executorInterventionEnabled = true,
    String executorMode = "ON",
  }) {
    final ws = ref.read(webSocketServiceProvider);
    ws.startSquad(
      task: task,
      provider: provider,
      modelName: modelName,
      targetLanguage: targetLanguage,
      maxIterations: maxIterations,
      executorInterventionEnabled: executorInterventionEnabled,
      executorMode: executorMode,
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
