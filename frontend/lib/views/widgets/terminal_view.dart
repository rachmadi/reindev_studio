import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/squad_pipeline_provider.dart';

// ---------------------------------------------------------------------------
// REQ-029 — Console Sandbox Terminal
// Displays colored terminal output for pytest / dart test results.
// - Black background, monospace font
// - Green for passed tests, red for failures, amber for warnings
// - ANSI-strip + colored line classification
// - Auto-scroll to latest entry
// ---------------------------------------------------------------------------

class TerminalView extends ConsumerStatefulWidget {
  const TerminalView({super.key});

  @override
  ConsumerState<TerminalView> createState() => _TerminalViewState();
}

class _TerminalViewState extends ConsumerState<TerminalView> {
  final ScrollController _scrollController = ScrollController();
  bool _autoScroll = true;

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_autoScroll &&
          _scrollController.hasClients &&
          _scrollController.position.maxScrollExtent > 0) {
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
    final logs = ref.watch(terminalLogsProvider);

    // Auto-scroll whenever logs change
    _scrollToBottom();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Terminal toolbar
        _buildToolbar(context, logs),

        // Terminal body
        Expanded(
          child: Container(
            color: const Color(0xFF0D0E14),
            child: logs.isEmpty
                ? _buildIdlePrompt()
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(12),
                    itemCount: logs.length,
                    itemBuilder: (context, index) =>
                        _TerminalLine(entry: logs[index]),
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildToolbar(BuildContext context, List<TerminalEntry> logs) {
    final theme = Theme.of(context);
    final stats = ref.watch(terminalStatsProvider);
    final int passed = stats.hasRun
        ? stats.passed
        : (logs.any((e) => e.type == TerminalLineType.pass) ? 1 : 0);
    final int failed = stats.hasRun
        ? stats.failed
        : (logs.any((e) => e.type == TerminalLineType.fail) ? 1 : 0);

    return Container(
      height: 36,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1D27),
        border: Border(
          bottom: BorderSide(
            color: theme.colorScheme.outlineVariant.withAlpha(60),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Traffic lights
          _trafficLight(const Color(0xFFEF4444)),
          const SizedBox(width: 6),
          _trafficLight(const Color(0xFFF59E0B)),
          const SizedBox(width: 6),
          _trafficLight(const Color(0xFF10B981)),
          const SizedBox(width: 12),

          Text(
            'SANDBOX TERMINAL',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: const Color(0xFF6B7280),
            ),
          ),
          const Spacer(),

          // Stats
          if (logs.isNotEmpty) ...[
            if (passed > 0)
              _statChip('$passed PASS', const Color(0xFF10B981)),
            if (failed > 0) ...[
              const SizedBox(width: 6),
              _statChip('$failed FAIL', const Color(0xFFEF4444)),
            ],
            const SizedBox(width: 8),
          ],

          // Auto-scroll toggle
          GestureDetector(
            onTap: () => setState(() => _autoScroll = !_autoScroll),
            child: Row(
              children: [
                Icon(
                  Icons.vertical_align_bottom_rounded,
                  size: 13,
                  color: _autoScroll
                      ? const Color(0xFF10B981)
                      : const Color(0xFF6B7280),
                ),
                const SizedBox(width: 4),
                Text(
                  'Auto',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    color: _autoScroll
                        ? const Color(0xFF10B981)
                        : const Color(0xFF6B7280),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _trafficLight(Color color) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }

  Widget _statChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: color.withAlpha(40),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withAlpha(100), width: 1),
      ),
      child: Text(
        label,
        style: GoogleFonts.jetBrainsMono(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }

  Widget _buildIdlePrompt() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '▌',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 20,
              color: const Color(0xFF10B981),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'reindev-studio \$ _',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 13,
              color: const Color(0xFF4B5568),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Menunggu eksekusi dart test / pytest...',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              color: const Color(0xFF374151),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Single colored terminal line widget
// ---------------------------------------------------------------------------
class _TerminalLine extends StatelessWidget {
  final TerminalEntry entry;

  const _TerminalLine({required this.entry});

  Color get _textColor {
    switch (entry.type) {
      case TerminalLineType.pass:
        return const Color(0xFF10B981);
      case TerminalLineType.fail:
        return const Color(0xFFEF4444);
      case TerminalLineType.warning:
        return const Color(0xFFF59E0B);
      case TerminalLineType.info:
        return const Color(0xFF3B82F6);
      case TerminalLineType.header:
        return const Color(0xFF8B5CF6);
      case TerminalLineType.prompt:
        return const Color(0xFF10B981);
      case TerminalLineType.normal:
        return const Color(0xFFD1D5DB);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isHeader = entry.type == TerminalLineType.header;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Prompt for header lines
          if (isHeader)
            Text(
              '▶ ',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 12,
                color: const Color(0xFF8B5CF6),
              ),
            ),
          // Content
          Expanded(
            child: Text(
              entry.text,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 12,
                height: 1.5,
                color: _textColor,
                fontWeight: isHeader ? FontWeight.w700 : FontWeight.w400,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
