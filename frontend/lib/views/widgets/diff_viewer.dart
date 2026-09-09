import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/squad_pipeline_provider.dart';

// ---------------------------------------------------------------------------
// REQ-030 — Visual Diff / Revision Viewer
// Shows file-level diffs produced when Developer self-heals after QA failure.
// - Unified diff format: removed lines (red -), added lines (green +)
// - File header per diff chunk
// - Empty state when no iterations have occurred yet
// ---------------------------------------------------------------------------

class DiffViewer extends ConsumerWidget {
  const DiffViewer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final diffs = ref.watch(diffEntriesProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header bar
        _buildHeader(context, diffs.length),

        // Diff content
        Expanded(
          child: diffs.isEmpty
              ? _buildEmptyState(theme)
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: diffs.length,
                  separatorBuilder: (context, idx) => const SizedBox(height: 12),
                  itemBuilder: (context, index) =>
                      _DiffChunk(entry: diffs[index]),
                ),
        ),
      ],
    );
  }

  Widget _buildHeader(BuildContext context, int count) {
    final theme = Theme.of(context);
    return Container(
      height: 36,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          bottom: BorderSide(
            color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.compare_rounded,
              size: 14, color: theme.colorScheme.primary),
          const SizedBox(width: 8),
          Text(
            'REVISION DIFF VIEWER',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const Spacer(),
          if (count > 0)
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withAlpha(30),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '$count revision${count == 1 ? '' : 's'}',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10,
                  color: theme.colorScheme.primary,
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.difference_outlined,
            size: 40,
            color: theme.colorScheme.onSurfaceVariant.withAlpha(120),
          ),
          const SizedBox(height: 12),
          Text(
            'Belum ada revisi',
            style: GoogleFonts.inter(
              fontSize: 13,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Diff muncul saat Developer melakukan\nself-healing setelah QA melaporkan kegagalan',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 11,
              color: theme.colorScheme.onSurfaceVariant.withAlpha(160),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Single diff chunk card (per file per iteration)
// ---------------------------------------------------------------------------
class _DiffChunk extends StatefulWidget {
  final DiffEntry entry;

  const _DiffChunk({required this.entry});

  @override
  State<_DiffChunk> createState() => _DiffChunkState();
}

class _DiffChunkState extends State<_DiffChunk> {
  bool _expanded = true;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final addedCount =
        widget.entry.lines.where((l) => l.type == DiffLineType.added).length;
    final removedCount =
        widget.entry.lines.where((l) => l.type == DiffLineType.removed).length;

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
          width: 1,
        ),
      ),
      child: Column(
        children: [
          // File header
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
            child: Container(
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainer,
                borderRadius: BorderRadius.vertical(
                  top: const Radius.circular(8),
                  bottom: _expanded ? Radius.zero : const Radius.circular(8),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_down_rounded
                        : Icons.keyboard_arrow_right_rounded,
                    size: 14,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 6),
                  Icon(Icons.edit_note_rounded,
                      size: 13, color: theme.colorScheme.primary),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      widget.entry.fileName,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                  ),
                  // Iteration badge
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: const Color(0xFF8B5CF6).withAlpha(30),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      'Iter ${widget.entry.iteration}',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 10,
                        color: const Color(0xFF8B5CF6),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  // +/- summary
                  Text(
                    '+$addedCount',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFF10B981),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '-$removedCount',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFFEF4444),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Diff lines
          if (_expanded)
            Container(
              decoration: const BoxDecoration(
                color: Color(0xFF0D0E14),
                borderRadius:
                    BorderRadius.vertical(bottom: Radius.circular(8)),
              ),
              constraints: const BoxConstraints(maxHeight: 320),
              child: SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 0, vertical: 4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: widget.entry.lines
                      .map((line) => _DiffLine(line: line))
                      .toList(),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Single diff line
// ---------------------------------------------------------------------------
class _DiffLine extends StatelessWidget {
  final DiffLine line;

  const _DiffLine({required this.line});

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color fg;
    String prefix;

    switch (line.type) {
      case DiffLineType.added:
        bg = const Color(0xFF10B981).withAlpha(25);
        fg = const Color(0xFF10B981);
        prefix = '+ ';
        break;
      case DiffLineType.removed:
        bg = const Color(0xFFEF4444).withAlpha(20);
        fg = const Color(0xFFEF4444);
        prefix = '- ';
        break;
      case DiffLineType.context:
        bg = Colors.transparent;
        fg = const Color(0xFF9CA3AF);
        prefix = '  ';
        break;
      case DiffLineType.hunk:
        bg = const Color(0xFF3B82F6).withAlpha(20);
        fg = const Color(0xFF60A5FA);
        prefix = '';
        break;
    }

    return Container(
      color: bg,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 1),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Line number gutter
          SizedBox(
            width: 36,
            child: Text(
              line.lineNumber != null ? '${line.lineNumber}' : '',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 11,
                color: const Color(0xFF4B5568),
              ),
            ),
          ),
          // Diff content
          Expanded(
            child: Text(
              '$prefix${line.content}',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 12,
                height: 1.5,
                color: fg,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
