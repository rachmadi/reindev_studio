import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/app_providers.dart';

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
    final theme = Theme.of(context);
    final agents = [
      {"role": "Product Manager", "desc": "Prinsip SMART & User Story", "icon": Icons.assignment_outlined, "status": "Ready"},
      {"role": "System Architect", "desc": "Modular File Tree & Contracts", "icon": Icons.account_tree_outlined, "status": "Ready"},
      {"role": "Developer", "desc": "Code Synthesizer & Sanitizer", "icon": Icons.code_rounded, "status": "Ready"},
      {"role": "QA Tester", "desc": "Automated Pytest & Assertions", "icon": Icons.biotech_outlined, "status": "Ready"},
      {"role": "Code Reviewer", "desc": "Security & Architecture Audit", "icon": Icons.verified_user_outlined, "status": "Ready"},
    ];

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Row(
          children: [
            Icon(Icons.device_hub_rounded, size: 20, color: theme.colorScheme.primary),
            const SizedBox(width: 8),
            Text(
              "AUTONOMOUS AGENT SQUAD TOPOLOGY",
              style: GoogleFonts.jetBrainsMono(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: theme.colorScheme.onSurfaceVariant,
                letterSpacing: 0.8,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final cardWidth = (constraints.maxWidth - (4 * 12)) / 5;
            final isNarrow = cardWidth < 140;

            if (isNarrow) {
              return Column(
                children: agents.map((agent) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _agentCard(context, agent),
                )).toList(),
              );
            }

            return Row(
              children: agents.map((agent) => Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  child: _agentCard(context, agent),
                ),
              )).toList(),
            );
          },
        ),
        const SizedBox(height: 24),

        // Stream Thought Container Preview
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.stream_rounded, size: 18, color: theme.colorScheme.secondary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        "Live Agent Thought & Collaboration Stream (Iterasi 5 Preview)",
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primaryContainer.withAlpha(120),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        "Idle / Menunggu Task",
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 11,
                          color: theme.colorScheme.onPrimaryContainer,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest.withAlpha(60),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: theme.colorScheme.outline.withAlpha(40),
                    ),
                  ),
                  child: Text(
                    "Studio siap menerima instruksi intensi rekayasa perangkat lunak.\nKetika 'Deploy Autonomous Squad' dieksekusi, aliran pemikiran, perancangan arsitektur, dan perbaikan siklus mandiri (Self-Healing Loop) akan disiarkan secara real-time di panel ini.",
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: theme.colorScheme.onSurfaceVariant,
                      height: 1.6,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _agentCard(BuildContext context, Map<String, dynamic> agent) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(agent["icon"] as IconData, size: 18, color: theme.colorScheme.primary),
                const Spacer(),
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    color: Color(0xFF10B981),
                    shape: BoxShape.circle,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              agent["role"] as String,
              style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w700),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              agent["desc"] as String,
              style: GoogleFonts.inter(fontSize: 10, color: theme.colorScheme.onSurfaceVariant),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
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
          Icon(Icons.circle, size: 8, color: theme.colorScheme.primary),
          const SizedBox(width: 8),
          Text(
            "Studio Ready",
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: theme.colorScheme.onSurface,
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
            "IIDD Cycle: Iterasi 3",
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