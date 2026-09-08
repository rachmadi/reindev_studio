import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../../models/agent_event.dart';
import '../../providers/squad_pipeline_provider.dart';
import '../../providers/app_providers.dart';

class ThoughtStreamViewer extends ConsumerStatefulWidget {
  const ThoughtStreamViewer({super.key});

  @override
  ConsumerState<ThoughtStreamViewer> createState() => _ThoughtStreamViewerState();
}

class _ThoughtStreamViewerState extends ConsumerState<ThoughtStreamViewer> {
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) return;
    final autoScroll = ref.read(autoScrollProvider);
    if (!autoScroll) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final allItems = ref.watch(thoughtStreamProvider);
    final currentFilter = ref.watch(streamFilterProvider);
    final autoScroll = ref.watch(autoScrollProvider);
    final squadStatus = ref.watch(squadStatusProvider);
    final activeRole = ref.watch(activeAgentRoleProvider);
    final elapsedSec = ref.watch(activeElapsedSecondsProvider);
    final missionDuration = ref.watch(missionDurationProvider);

    // Auto scroll listener
    ref.listen(thoughtStreamProvider, (previous, next) {
      if (next.length > (previous?.length ?? 0)) {
        _scrollToBottom();
      }
    });

    final filteredItems = currentFilter == null
        ? allItems
        : allItems.where((item) => item.agentRole == currentFilter).toList();

    return Card(
      elevation: 0,
      color: theme.colorScheme.surfaceContainerHighest.withAlpha(50),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: theme.colorScheme.outline.withAlpha(45),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Stream Header Bar
            _buildHeader(theme, squadStatus, activeRole, autoScroll, allItems.length, elapsedSec, missionDuration),
            const SizedBox(height: 12),

            // Filter Chips Bar
            _buildFilterBar(theme, currentFilter, allItems),
            const SizedBox(height: 14),
            const Divider(height: 1),
            const SizedBox(height: 14),

            // Stream Body List
            Expanded(
              child: filteredItems.isEmpty
                  ? _buildEmptyState(theme, currentFilter)
                  : SingleChildScrollView(
                      controller: _scrollController,
                      child: Column(
                        children: [
                          for (final item in filteredItems)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: _buildThoughtCard(context, item),
                            ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(
    ThemeData theme,
    String squadStatus,
    AgentRole? activeRole,
    bool autoScroll,
    int totalCount,
    String elapsedSec,
    double? missionDuration,
  ) {
    final isRunning = squadStatus == "running" || activeRole != null;
    final isCompleted = squadStatus == "completed";

    return Row(
      children: [
        Icon(
          Icons.stream_rounded,
          size: 18,
          color: isRunning ? const Color(0xFF3B82F6) : theme.colorScheme.secondary,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Row(
            children: [
              Flexible(
                child: Text(
                  "Live Agent Thought & Collaboration Stream",
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.onSurface,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withAlpha(30),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  "$totalCount",
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ),
            ],
          ),
        ),
        // Live Status Badge
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: isRunning
                ? const Color(0xFF3B82F6).withAlpha(40)
                : isCompleted
                    ? const Color(0xFF10B981).withAlpha(35)
                    : theme.colorScheme.surfaceContainerHighest.withAlpha(120),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: isRunning
                  ? const Color(0xFF3B82F6).withAlpha(90)
                  : isCompleted
                      ? const Color(0xFF10B981).withAlpha(90)
                      : theme.colorScheme.outline.withAlpha(50),
              width: 0.8,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (isRunning) ...[
                const SizedBox(
                  width: 10,
                  height: 10,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation(Color(0xFF3B82F6)),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  activeRole != null
                      ? (elapsedSec.isNotEmpty
                          ? "${activeRole.displayName} ($elapsedSec)"
                          : "${activeRole.displayName} Active")
                      : "Streaming...",
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF3B82F6),
                  ),
                ),
              ] else if (isCompleted) ...[
                const Icon(Icons.check_circle_rounded,
                    size: 13, color: Color(0xFF10B981)),
                const SizedBox(width: 5),
                Text(
                  missionDuration != null
                      ? "Selesai (${missionDuration.toStringAsFixed(1)}s)"
                      : "Selesai (Completed)",
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF10B981),
                  ),
                ),
              ] else ...[
                Icon(Icons.pause_circle_outline_rounded,
                    size: 13, color: theme.colorScheme.onSurfaceVariant),
                const SizedBox(width: 4),
                Text(
                  "Idle / Standby",
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ),
        ),

        const SizedBox(width: 8),
        // Auto-Scroll Toggle Button
        IconButton(
          icon: Icon(
            autoScroll ? Icons.vertical_align_bottom_rounded : Icons.pause_rounded,
            size: 18,
            color: autoScroll ? theme.colorScheme.primary : theme.colorScheme.onSurfaceVariant,
          ),
          tooltip: autoScroll ? "Auto-scroll: ON (Klik untuk jeda)" : "Auto-scroll: OFF",
          onPressed: () => ref.read(autoScrollProvider.notifier).toggle(),
        ),
        // Clear Log Button
        IconButton(
          icon: const Icon(Icons.delete_sweep_outlined, size: 18),
          tooltip: "Bersihkan stream log",
          onPressed: () {
            ref.read(thoughtStreamProvider.notifier).clear();
          },
        ),
      ],
    );
  }

  Widget _buildFilterBar(
    ThemeData theme,
    AgentRole? currentFilter,
    List<ThoughtItem> allItems,
  ) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          // All Filter Chip
          ChoiceChip(
            label: Text("All Events (${allItems.length})"),
            selected: currentFilter == null,
            onSelected: (_) =>
                ref.read(streamFilterProvider.notifier).setFilter(null),
            labelStyle: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: currentFilter == null ? FontWeight.w700 : FontWeight.w500,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
          ),
          const SizedBox(width: 6),
          // Per-agent chips
          ...AgentRole.values.map((role) {
            final count = allItems.where((i) => i.agentRole == role).length;
            final isSelected = currentFilter == role;

            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                avatar: Icon(role.icon, size: 13, color: isSelected ? Colors.white : role.accentColor),
                label: Text("${role.displayName} ($count)"),
                selected: isSelected,
                selectedColor: role.accentColor.withAlpha(200),
                onSelected: (val) {
                  ref
                      .read(streamFilterProvider.notifier)
                      .setFilter(val ? role : null);
                },
                labelStyle: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  color: isSelected ? Colors.white : theme.colorScheme.onSurface,
                ),
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme, AgentRole? filter) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.forum_outlined,
              size: 40,
              color: theme.colorScheme.outline.withAlpha(120),
            ),
            const SizedBox(height: 12),
            Text(
              filter == null
                  ? "Belum ada aliran pemikiran agen."
                  : "Tidak ada log pemikiran untuk ${filter.displayName}.",
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              "Ketik deskripsi fitur di panel kiri dan klik 'Deploy Autonomous Squad' untuk menyaksikan pemikiran, arsitektur, dan eksekusi tes secara real-time.",
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                fontSize: 11,
                color: theme.colorScheme.onSurfaceVariant.withAlpha(150),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThoughtCard(BuildContext context, ThoughtItem item) {
    final theme = Theme.of(context);
    final timeStr =
        "${item.timestamp.hour.toString().padLeft(2, '0')}:${item.timestamp.minute.toString().padLeft(2, '0')}:${item.timestamp.second.toString().padLeft(2, '0')}";

    final isCodeOrTest = item.type == 'code' || item.type == 'test';

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: theme.colorScheme.outline.withAlpha(35),
          width: 0.8,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              width: 4,
              color: item.agentRole.accentColor,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Card Header Row
                    Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: item.agentRole.accentColor.withAlpha(35),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(
                    item.agentRole.icon,
                    size: 14,
                    color: item.agentRole.accentColor,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  item.agentRole.displayName,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: item.agentRole.accentColor,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest.withAlpha(100),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    item.type.toUpperCase(),
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
                const Spacer(),
                Text(
                  timeStr,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    color: theme.colorScheme.onSurfaceVariant.withAlpha(150),
                  ),
                ),
                const SizedBox(width: 4),
                IconButton(
                  icon: const Icon(Icons.copy_rounded, size: 14),
                  tooltip: "Salin isi",
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: item.content));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text("Konten pemikiran berhasil disalin ke clipboard."),
                        duration: Duration(seconds: 1),
                      ),
                    );
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Phase Title
            Text(
              item.title,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 8),

            // Content Body
            if (item.isCollapsible && !item.isExpanded) ...[
              InkWell(
                onTap: () =>
                    ref.read(thoughtStreamProvider.notifier).toggleExpand(item.id),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      Icon(Icons.expand_more_rounded,
                          size: 16, color: theme.colorScheme.primary),
                      const SizedBox(width: 4),
                      Text(
                        "Tampilkan rincian selengkapnya...",
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ] else ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: isCodeOrTest
                      ? (theme.brightness == Brightness.dark
                          ? const Color(0xFF0F172A)
                          : const Color(0xFFF1F5F9))
                      : theme.colorScheme.surfaceContainerHighest.withAlpha(50),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: theme.colorScheme.outline.withAlpha(25),
                  ),
                ),
                child: isCodeOrTest && !item.content.trim().startsWith('```')
                    ? SelectableText(
                        item.content,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 11,
                          height: 1.5,
                          color: theme.colorScheme.onSurface,
                        ),
                      )
                    : MarkdownBody(
                        data: item.content,
                        selectable: true,
                        styleSheet: MarkdownStyleSheet.fromTheme(theme).copyWith(
                          p: GoogleFonts.inter(
                            fontSize: 12,
                            height: 1.5,
                            color: theme.colorScheme.onSurface,
                          ),
                          h1: GoogleFonts.inter(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: theme.colorScheme.onSurface,
                          ),
                          h2: GoogleFonts.inter(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700,
                            color: theme.colorScheme.onSurface,
                          ),
                          h3: GoogleFonts.inter(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: theme.colorScheme.onSurface,
                          ),
                          strong: GoogleFonts.inter(
                            fontWeight: FontWeight.w700,
                            color: theme.colorScheme.onSurface,
                          ),
                          em: GoogleFonts.inter(
                            fontStyle: FontStyle.italic,
                            color: theme.colorScheme.onSurface,
                          ),
                          listBullet: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: item.agentRole.accentColor,
                          ),
                          code: GoogleFonts.jetBrainsMono(
                            fontSize: 11,
                            backgroundColor: theme.brightness == Brightness.dark
                                ? const Color(0xFF1E293B)
                                : const Color(0xFFE2E8F0),
                            color: theme.colorScheme.primary,
                          ),
                          codeblockDecoration: BoxDecoration(
                            color: theme.brightness == Brightness.dark
                                ? const Color(0xFF0F172A)
                                : const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: theme.colorScheme.outline.withAlpha(30),
                            ),
                          ),
                          codeblockPadding: const EdgeInsets.all(10),
                          blockquoteDecoration: BoxDecoration(
                            border: Border(
                              left: BorderSide(
                                color: item.agentRole.accentColor,
                                width: 3,
                              ),
                            ),
                          ),
                          blockquotePadding: const EdgeInsets.only(left: 10, top: 4, bottom: 4),
                        ),
                      ),
              ),
              if (item.isCollapsible)
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    icon: const Icon(Icons.expand_less_rounded, size: 14),
                    label: Text(
                      "Sembunyikan",
                      style: GoogleFonts.inter(fontSize: 10.5),
                    ),
                    onPressed: () => ref
                        .read(thoughtStreamProvider.notifier)
                        .toggleExpand(item.id),
                  ),
                ),
            ],
          ],
        ),
      ),
    ),
  ],
),
),
);
  }
}
