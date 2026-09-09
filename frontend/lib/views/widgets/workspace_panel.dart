import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/app_providers.dart';
import '../../providers/squad_pipeline_provider.dart';
import 'agent_cards.dart';
import 'code_viewer.dart';
import 'file_explorer.dart';
import 'quality_review_panel.dart';
import 'terminal_view.dart';
import 'thought_stream.dart';

class WorkspacePanel extends ConsumerStatefulWidget {
  const WorkspacePanel({super.key});

  @override
  ConsumerState<WorkspacePanel> createState() => _WorkspacePanelState();
}

class _WorkspacePanelState extends ConsumerState<WorkspacePanel>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) {
        ref.read(activeWorkspaceTabProvider.notifier).setTab(
            _tabController.index);
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      children: [
        // Tab Navigation Header
        Container(
          height: 48,
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            border: Border(
              bottom: BorderSide(
                color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
                width: 1,
              ),
            ),
          ),
          child: TabBar(
            controller: _tabController,
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            tabs: const [
              Tab(
                icon: Icon(Icons.hub_rounded, size: 16),
                text: "Agent Squad Timeline",
              ),
              Tab(
                icon: Icon(Icons.code_rounded, size: 16),
                text: "Code Canvas & Explorer",
              ),
              Tab(
                icon: Icon(Icons.terminal_rounded, size: 16),
                text: "Sandbox Terminal",
              ),
              Tab(
                icon: Icon(Icons.fact_check_rounded, size: 16),
                text: "Quality & Review Report",
              ),
            ],
          ),
        ),

        // Tab Content Area
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildTimelineTab(context),
              _buildCodeExplorerTab(context),
              _buildTerminalTab(context),
              _buildReviewTab(context),
            ],
          ),
        ),

        // Workspace Bottom Status Bar
        _buildStatusBar(context),
      ],
    );
  }

  Widget _buildTimelineTab(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          // 5 Interactive Agent Cards with Pulsing Indicator (REQ-023, REQ-026)
          AgentCardsRow(),
          SizedBox(height: 18),
          // Live Auto-scrolling Thought & Discussion Stream (REQ-024, REQ-025)
          Expanded(
            child: ThoughtStreamViewer(),
          ),
        ],
      ),
    );
  }

  Widget _buildCodeExplorerTab(BuildContext context) {
    return Row(
      children: [
        // Left: File Tree Explorer (REQ-027)
        SizedBox(
          width: 220,
          child: const FileTreeExplorer(),
        ),
        // Right: Syntax-highlighted Code Viewer (REQ-028)
        const Expanded(
          child: CodeViewer(),
        ),
      ],
    );
  }

  Widget _buildTerminalTab(BuildContext context) {
    // REQ-029 — Sandbox Terminal with colored test output
    return const TerminalView();
  }

  Widget _buildReviewTab(BuildContext context) {
    // REQ-010 & REQ-030 — Code Reviewer Audit Report & Revision Diff Viewer
    return const QualityReviewPanel();
  }

  Widget _buildStatusBar(BuildContext context) {
    final theme = Theme.of(context);
    final squadStatus = ref.watch(squadStatusProvider);
    final missionDuration = ref.watch(missionDurationProvider);
    final loopState = ref.watch(loopStatusProvider);
    final executorIntervention = ref.watch(executorInterventionProvider);
    final executorMode = ref.watch(executorModeProvider);
    final isCompleted = squadStatus == 'completed';
    final isNeedsRevision = squadStatus == 'needs_revision';
    final isRunning = squadStatus == 'running';

    // Format status teks putaran loop self-healing
    String loopText;
    Color loopColor;
    if (isRunning) {
      if (loopState.currentLoop > 0) {
        loopText = "Self-Healing: Loop ${loopState.currentLoop}/${loopState.maxLoops} (Berjalan)";
        loopColor = const Color(0xFFF59E0B);
      } else {
        loopText = "Self-Healing: Loop 0/${loopState.maxLoops} (First-Pass)";
        loopColor = const Color(0xFF3B82F6);
      }
    } else if (isCompleted) {
      if (loopState.currentLoop == 0) {
        loopText = "Self-Healing: Tuntas pada Loop 0/${loopState.maxLoops} (First-Pass)";
      } else {
        loopText = "Self-Healing: Tuntas pada Loop ${loopState.currentLoop}/${loopState.maxLoops}";
      }
      loopColor = const Color(0xFF10B981);
    } else if (isNeedsRevision) {
      loopText = "Self-Healing: Berakhir di Loop ${loopState.currentLoop}/${loopState.maxLoops} (Maksimum)";
      loopColor = const Color(0xFFEF4444);
    } else {
      loopText = "Self-Healing: Max ${loopState.maxLoops} Loops";
      loopColor = theme.colorScheme.onSurfaceVariant;
    }

    return Container(
      height: 32,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          Icon(
            isCompleted
                ? Icons.check_circle_rounded
                : isNeedsRevision
                    ? Icons.warning_amber_rounded
                    : isRunning
                        ? Icons.sync_rounded
                        : Icons.circle,
            size: (isCompleted || isNeedsRevision) ? 14 : 8,
            color: isCompleted
                ? const Color(0xFF10B981)
                : isNeedsRevision
                    ? const Color(0xFFF59E0B)
                    : isRunning
                        ? const Color(0xFF3B82F6)
                        : theme.colorScheme.primary,
          ),
          Expanded(
            child: Text(
              isCompleted
                  ? (missionDuration != null
                      ? "Mission Selesai (Approved) • Total Waktu: ${missionDuration.toStringAsFixed(1)} detik"
                      : "Mission Selesai (Approved)")
                  : isNeedsRevision
                      ? (missionDuration != null
                          ? "Mission Selesai (Perlu Revisi) • Total Waktu: ${missionDuration.toStringAsFixed(1)} detik"
                          : "Mission Selesai (Perlu Revisi)")
                      : isRunning
                          ? "Squad Sedang Bekerja..."
                          : "Studio Ready",
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 11,
                fontWeight: (isCompleted || isNeedsRevision) ? FontWeight.w700 : FontWeight.w500,
                color: isCompleted
                    ? const Color(0xFF10B981)
                    : isNeedsRevision
                        ? const Color(0xFFF59E0B)
                        : theme.colorScheme.onSurface,
              ),
            ),
          ),
          const SizedBox(width: 16),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.repeat_rounded,
                size: 13,
                color: loopColor,
              ),
              const SizedBox(width: 4),
              Text(
                loopText,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: loopColor,
                ),
              ),
            ],
          ),
          const SizedBox(width: 16),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                executorMode == "ON"
                    ? Icons.auto_fix_high_rounded
                    : (executorMode == "CODE_ONLY"
                        ? Icons.code_rounded
                        : Icons.block_rounded),
                size: 13,
                color: executorMode == "ON"
                    ? const Color(0xFF10B981)
                    : (executorMode == "CODE_ONLY"
                        ? const Color(0xFF06B6D4)
                        : const Color(0xFFF59E0B)),
              ),
              const SizedBox(width: 4),
              Text(
                "Executor: $executorMode",
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: executorMode == "ON"
                      ? const Color(0xFF10B981)
                      : (executorMode == "CODE_ONLY"
                          ? const Color(0xFF06B6D4)
                          : const Color(0xFFF59E0B)),
                ),
              ),
            ],
          ),
          const SizedBox(width: 16),
          Text(
            "IIDD Cycle: Iterasi 6",
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}