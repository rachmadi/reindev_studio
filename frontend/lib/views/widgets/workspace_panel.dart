import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/app_providers.dart';
import '../../providers/squad_pipeline_provider.dart';
import 'agent_cards.dart';
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
    final theme = Theme.of(context);
    return Center(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.folder_open_rounded, size: 48, color: theme.colorScheme.primary),
              const SizedBox(height: 16),
              Text(
                "Code Canvas & File Tree Explorer",
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                "Fitur navigasi berkas, syntax highlighting, dan inspeksi kode akan diaktifkan penuh pada Iterasi 6.",
                style: GoogleFonts.inter(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTerminalTab(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.terminal_rounded, size: 48, color: theme.colorScheme.secondary),
              const SizedBox(height: 16),
              Text(
                "Subprocess Sandbox Terminal",
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                "Output eksekusi pytest dan dart analyze langsung dari subproses terisolasi.",
                style: GoogleFonts.inter(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildReviewTab(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.verified_user_rounded, size: 48, color: const Color(0xFF10B981)),
              const SizedBox(height: 16),
              Text(
                "Code Reviewer & Governance Report",
                style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                "Laporan audit keamanan, kualitas modularitas, dan status persetujuan rilis produk.",
                style: GoogleFonts.inter(fontSize: 12, color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusBar(BuildContext context) {
    final theme = Theme.of(context);
    final squadStatus = ref.watch(squadStatusProvider);
    final missionDuration = ref.watch(missionDurationProvider);
    final isCompleted = squadStatus == 'completed';
    final isRunning = squadStatus == 'running';

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
                : isRunning
                    ? Icons.sync_rounded
                    : Icons.circle,
            size: isCompleted ? 13 : 8,
            color: isCompleted
                ? const Color(0xFF10B981)
                : isRunning
                    ? const Color(0xFF3B82F6)
                    : theme.colorScheme.primary,
          ),
          const SizedBox(width: 8),
          Text(
            isCompleted
                ? (missionDuration != null
                    ? "Mission Selesai • Total Waktu: ${missionDuration.toStringAsFixed(1)} detik"
                    : "Mission Selesai (Completed)")
                : isRunning
                    ? "Squad Sedang Bekerja..."
                    : "Studio Ready",
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: isCompleted ? FontWeight.w700 : FontWeight.w500,
              color: isCompleted
                  ? const Color(0xFF10B981)
                  : theme.colorScheme.onSurface,
            ),
          ),
          const Spacer(),
          Text(
            "Self-Healing: Max 3 Loops",
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(width: 16),
          Text(
            "IIDD Cycle: Iterasi 5",
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