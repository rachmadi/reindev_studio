import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/squad_pipeline_provider.dart';

// ---------------------------------------------------------------------------
// REQ-027 — Interactive File Tree Explorer
// Displays the generated project file tree from code_update events.
// Clicking a file node updates selectedFileProvider in Code Canvas tab.
// ---------------------------------------------------------------------------

class FileTreeExplorer extends ConsumerWidget {
  const FileTreeExplorer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final files = ref.watch(codeFilesProvider);
    final selectedFile = ref.watch(selectedFileProvider);

    if (files.isEmpty) {
      return _buildEmptyState(theme);
    }

    // Build virtual tree from flat file map keys
    final tree = _buildFileTree(files.keys.toList());

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        border: Border(
          right: BorderSide(
            color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
            width: 1,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Container(
            height: 36,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              border: Border(
                bottom: BorderSide(
                  color: theme.dividerTheme.color ??
                      theme.colorScheme.outlineVariant,
                  width: 1,
                ),
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.folder_open_rounded,
                    size: 14, color: theme.colorScheme.primary),
                const SizedBox(width: 6),
                Text(
                  'PROJECT FILES',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const Spacer(),
                Text(
                  '${files.length} files',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),

          // Tree
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 4),
              children: _buildTreeWidgets(
                context,
                ref,
                tree,
                selectedFile,
                0,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        border: Border(
          right: BorderSide(
            color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
            width: 1,
          ),
        ),
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.folder_off_rounded,
              size: 32,
              color: theme.colorScheme.onSurfaceVariant.withAlpha(120),
            ),
            const SizedBox(height: 12),
            Text(
              'Belum ada file',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Deploy Squad untuk\nmemulai generasi kode',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                fontSize: 11,
                color: theme.colorScheme.onSurfaceVariant.withAlpha(160),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Build a nested Map<String, dynamic> representing the directory tree
  Map<String, dynamic> _buildFileTree(List<String> paths) {
    final Map<String, dynamic> root = {};
    for (final path in paths) {
      final parts = path.replaceAll('\\', '/').split('/');
      Map<String, dynamic> current = root;
      for (int i = 0; i < parts.length; i++) {
        final part = parts[i];
        if (i == parts.length - 1) {
          // leaf = file, store full path as value
          current[part] = path;
        } else {
          current.putIfAbsent(part, () => <String, dynamic>{});
          current = current[part] as Map<String, dynamic>;
        }
      }
    }
    return root;
  }

  List<Widget> _buildTreeWidgets(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> node,
    String? selectedFile,
    int depth,
  ) {
    final entries = node.entries.toList()
      ..sort((a, b) {
        // Directories first, then files
        final aIsDir = a.value is Map;
        final bIsDir = b.value is Map;
        if (aIsDir && !bIsDir) return -1;
        if (!aIsDir && bIsDir) return 1;
        return a.key.compareTo(b.key);
      });

    return entries.map((entry) {
      if (entry.value is Map) {
        return _DirectoryNode(
          name: entry.key,
          children: entry.value as Map<String, dynamic>,
          depth: depth,
          selectedFile: selectedFile,
          onFileSelected: (path) =>
              ref.read(selectedFileProvider.notifier).select(path),
        );
      } else {
        // Leaf file node
        final filePath = entry.value as String;
        final isSelected = selectedFile == filePath;
        return _FileNode(
          name: entry.key,
          filePath: filePath,
          depth: depth,
          isSelected: isSelected,
          onTap: () => ref.read(selectedFileProvider.notifier).select(filePath),
        );
      }
    }).toList();
  }
}

// ---------------------------------------------------------------------------
// Directory node (expandable)
// ---------------------------------------------------------------------------
class _DirectoryNode extends StatefulWidget {
  final String name;
  final Map<String, dynamic> children;
  final int depth;
  final String? selectedFile;
  final void Function(String) onFileSelected;

  const _DirectoryNode({
    required this.name,
    required this.children,
    required this.depth,
    required this.selectedFile,
    required this.onFileSelected,
  });

  @override
  State<_DirectoryNode> createState() => _DirectoryNodeState();
}

class _DirectoryNodeState extends State<_DirectoryNode> {
  bool _expanded = true;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final indent = 12.0 + widget.depth * 14.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InkWell(
          onTap: () => setState(() => _expanded = !_expanded),
          child: Container(
            height: 28,
            padding: EdgeInsets.only(left: indent, right: 8),
            child: Row(
              children: [
                Icon(
                  _expanded
                      ? Icons.keyboard_arrow_down_rounded
                      : Icons.keyboard_arrow_right_rounded,
                  size: 14,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Icon(
                  _expanded
                      ? Icons.folder_open_rounded
                      : Icons.folder_rounded,
                  size: 14,
                  color: const Color(0xFFF59E0B),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    widget.name,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 12,
                      color: theme.colorScheme.onSurface,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        if (_expanded)
          ..._buildChildWidgets(context),
      ],
    );
  }

  List<Widget> _buildChildWidgets(BuildContext context) {
    final entries = widget.children.entries.toList()
      ..sort((a, b) {
        final aIsDir = a.value is Map;
        final bIsDir = b.value is Map;
        if (aIsDir && !bIsDir) return -1;
        if (!aIsDir && bIsDir) return 1;
        return a.key.compareTo(b.key);
      });

    return entries.map((entry) {
      if (entry.value is Map) {
        return _DirectoryNode(
          name: entry.key,
          children: entry.value as Map<String, dynamic>,
          depth: widget.depth + 1,
          selectedFile: widget.selectedFile,
          onFileSelected: widget.onFileSelected,
        );
      } else {
        final filePath = entry.value as String;
        return _FileNode(
          name: entry.key,
          filePath: filePath,
          depth: widget.depth + 1,
          isSelected: widget.selectedFile == filePath,
          onTap: () => widget.onFileSelected(filePath),
        );
      }
    }).toList();
  }
}

// ---------------------------------------------------------------------------
// File leaf node
// ---------------------------------------------------------------------------
class _FileNode extends StatelessWidget {
  final String name;
  final String filePath;
  final int depth;
  final bool isSelected;
  final VoidCallback onTap;

  const _FileNode({
    required this.name,
    required this.filePath,
    required this.depth,
    required this.isSelected,
    required this.onTap,
  });

  IconData get _icon {
    final ext = name.split('.').last.toLowerCase();
    switch (ext) {
      case 'dart':
        return Icons.flutter_dash;
      case 'py':
        return Icons.code_rounded;
      case 'yaml':
      case 'yml':
        return Icons.settings_rounded;
      case 'json':
        return Icons.data_object_rounded;
      case 'md':
        return Icons.article_rounded;
      case 'txt':
        return Icons.text_snippet_rounded;
      default:
        return Icons.insert_drive_file_rounded;
    }
  }

  Color _iconColor(ThemeData theme) {
    final ext = name.split('.').last.toLowerCase();
    switch (ext) {
      case 'dart':
        return const Color(0xFF54C5F8);
      case 'py':
        return const Color(0xFF3B82F6);
      case 'yaml':
      case 'yml':
        return const Color(0xFF8B5CF6);
      case 'json':
        return const Color(0xFFF59E0B);
      case 'md':
        return const Color(0xFF10B981);
      default:
        return theme.colorScheme.onSurfaceVariant;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final indent = 12.0 + depth * 14.0 + 18.0; // extra 18 for caret space

    return Material(
      color: isSelected
          ? theme.colorScheme.primary.withAlpha(30)
          : Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Container(
          height: 26,
          padding: EdgeInsets.only(left: indent, right: 8),
          decoration: isSelected
              ? BoxDecoration(
                  border: Border(
                    left: BorderSide(
                      color: theme.colorScheme.primary,
                      width: 2,
                    ),
                  ),
                )
              : null,
          child: Row(
            children: [
              Icon(_icon, size: 13, color: _iconColor(theme)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  name,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 12,
                    fontWeight:
                        isSelected ? FontWeight.w600 : FontWeight.w400,
                    color: isSelected
                        ? theme.colorScheme.primary
                        : theme.colorScheme.onSurface,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
