import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/atom-one-dark.dart';
import 'package:flutter_highlight/themes/atom-one-light.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/squad_pipeline_provider.dart';

// ---------------------------------------------------------------------------
// REQ-028 — Syntax-Highlighted Code Canvas Viewer
// Displays selected file content with:
// - Syntax highlighting (flutter_highlight, language auto-detected)
// - Line numbers
// - Copy Code button
// - File size info
// ---------------------------------------------------------------------------

class CodeViewer extends ConsumerStatefulWidget {
  const CodeViewer({super.key});

  @override
  ConsumerState<CodeViewer> createState() => _CodeViewerState();
}

class _CodeViewerState extends ConsumerState<CodeViewer> {
  bool _copied = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final selectedFile = ref.watch(selectedFileProvider);
    final files = ref.watch(codeFilesProvider);

    if (selectedFile == null || !files.containsKey(selectedFile)) {
      return _buildPlaceholder(theme);
    }

    final content = files[selectedFile] ?? '';
    final language = _detectLanguage(selectedFile);
    final lineCount = '\n'.allMatches(content).length + 1;
    final sizeKb = (content.length / 1024).toStringAsFixed(1);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Toolbar
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
              Icon(Icons.code_rounded,
                  size: 14, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  selectedFile.replaceAll('\\', '/').split('/').last,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: theme.colorScheme.onSurface,
                  ),
                ),
              ),

              // File stats
              Text(
                '$lineCount lines • $sizeKb KB • $language',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(width: 12),

              // Copy button
              SizedBox(
                height: 24,
                child: TextButton.icon(
                  style: TextButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
                    visualDensity: VisualDensity.compact,
                    foregroundColor: _copied
                        ? const Color(0xFF10B981)
                        : theme.colorScheme.primary,
                  ),
                  onPressed: () => _copyToClipboard(content),
                  icon: Icon(
                    _copied
                        ? Icons.check_circle_outline_rounded
                        : Icons.copy_rounded,
                    size: 13,
                  ),
                  label: Text(
                    _copied ? 'Tersalin!' : 'Copy Code',
                    style: GoogleFonts.inter(fontSize: 11),
                  ),
                ),
              ),
            ],
          ),
        ),

        // Code area with line numbers
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Line numbers gutter
              Container(
                width: 44,
                color: isDark
                    ? const Color(0xFF1A1D27)
                    : const Color(0xFFF0F2F5),
                child: SingleChildScrollView(
                  physics: const NeverScrollableScrollPhysics(),
                  child: _buildLineNumbers(lineCount, theme, isDark),
                ),
              ),

              // Highlighted code
              Expanded(
                child: _HighlightedCodeView(
                  code: content,
                  language: language,
                  isDark: isDark,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLineNumbers(int count, ThemeData theme, bool isDark) {
    return Column(
      children: List.generate(count, (i) {
        return SizedBox(
          height: 20,
          child: Align(
            alignment: Alignment.centerRight,
            child: Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Text(
                '${i + 1}',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 12,
                  height: 1.4,
                  color: isDark
                      ? const Color(0xFF4B5568)
                      : const Color(0xFFA0AEC0),
                ),
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget _buildPlaceholder(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.code_off_rounded,
            size: 40,
            color: theme.colorScheme.onSurfaceVariant.withAlpha(120),
          ),
          const SizedBox(height: 12),
          Text(
            'Pilih file dari explorer',
            style: GoogleFonts.inter(
              fontSize: 13,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Klik nama file di panel kiri untuk melihat kode',
            style: GoogleFonts.inter(
              fontSize: 11,
              color: theme.colorScheme.onSurfaceVariant.withAlpha(160),
            ),
          ),
        ],
      ),
    );
  }

  String _detectLanguage(String path) {
    final ext = path.split('.').last.toLowerCase();
    switch (ext) {
      case 'dart':
        return 'dart';
      case 'py':
        return 'python';
      case 'yaml':
      case 'yml':
        return 'yaml';
      case 'json':
        return 'json';
      case 'md':
        return 'markdown';
      case 'sh':
      case 'bat':
        return 'bash';
      case 'js':
      case 'ts':
        return 'javascript';
      default:
        return 'plaintext';
    }
  }

  Future<void> _copyToClipboard(String content) async {
    await Clipboard.setData(ClipboardData(text: content));
    if (mounted) {
      setState(() => _copied = true);
    }
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) {
      setState(() => _copied = false);
    }
  }
}

// ---------------------------------------------------------------------------
// Scrollable syntax-highlighted view using flutter_highlight
// ---------------------------------------------------------------------------
class _HighlightedCodeView extends StatelessWidget {
  final String code;
  final String language;
  final bool isDark;

  const _HighlightedCodeView({
    required this.code,
    required this.language,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final bgColor =
        isDark ? const Color(0xFF1E2233) : const Color(0xFFFAFAFB);
    final theme = isDark ? atomOneDarkTheme : atomOneLightTheme;

    return Container(
      color: bgColor,
      child: SingleChildScrollView(
        scrollDirection: Axis.vertical,
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: HighlightView(
            code,
            language: language,
            theme: theme,
            padding: const EdgeInsets.fromLTRB(12, 8, 24, 8),
            textStyle: GoogleFonts.jetBrainsMono(
              fontSize: 12.5,
              height: 1.55,
            ),
          ),
        ),
      ),
    );
  }
}
