import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/squad_pipeline_provider.dart';
import 'diff_viewer.dart';

/// ---------------------------------------------------------------------------
/// REQ-010 & REQ-030 — Comprehensive Quality & Review Report Panel
///
/// Combines:
/// 1. Official Code Reviewer & Security Audit Report (REQ-010)
/// 2. Revision Diff Viewer for self-healing loops (REQ-030)
/// ---------------------------------------------------------------------------

class QualityReviewPanel extends ConsumerStatefulWidget {
  const QualityReviewPanel({super.key});

  @override
  ConsumerState<QualityReviewPanel> createState() => _QualityReviewPanelState();
}

class _QualityReviewPanelState extends ConsumerState<QualityReviewPanel> {
  int _selectedSubTab = 0; // 0 = Reviewer Audit Report, 1 = Revision Diff History

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final reviewState = ref.watch(reviewReportProvider);
    final diffs = ref.watch(diffEntriesProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Top Toolbar with Sub-tab Switcher and Status Chip
        _buildToolbar(context, reviewState, diffs.length),

        // Active Content Body
        Expanded(
          child: _selectedSubTab == 0
              ? _buildReviewReportTab(context, reviewState, isDark)
              : _buildDiffHistoryTab(context, diffs, reviewState, isDark),
        ),
      ],
    );
  }

  Widget _buildToolbar(
      BuildContext context, ReviewReportState reviewState, int diffCount) {
    final theme = Theme.of(context);
    final isApproved = reviewState.isApproved;

    return Container(
      height: 42,
      padding: const EdgeInsets.symmetric(horizontal: 14),
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
          Icon(
            Icons.verified_user_rounded,
            size: 16,
            color: isApproved ? const Color(0xFF10B981) : const Color(0xFF6B7280),
          ),
          const SizedBox(width: 8),
          Text(
            'QUALITY & REVIEW REPORT',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: theme.colorScheme.onSurface,
            ),
          ),
          const SizedBox(width: 12),

          // Status Badge
          if (!reviewState.isEmpty)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: isApproved
                    ? const Color(0xFF10B981).withAlpha(35)
                    : const Color(0xFFF59E0B).withAlpha(35),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isApproved
                      ? const Color(0xFF10B981).withAlpha(120)
                      : const Color(0xFFF59E0B).withAlpha(120),
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isApproved ? Icons.check_circle_rounded : Icons.pending_rounded,
                    size: 12,
                    color: isApproved
                        ? const Color(0xFF10B981)
                        : const Color(0xFFF59E0B),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    isApproved ? 'RELEASE APPROVED' : 'NEEDS REVISION',
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: isApproved
                          ? const Color(0xFF10B981)
                          : const Color(0xFFF59E0B),
                    ),
                  ),
                ],
              ),
            ),

          const Spacer(),

          // Sub-Tab Switcher
          Container(
            height: 28,
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest.withAlpha(120),
              borderRadius: BorderRadius.circular(6),
            ),
            padding: const EdgeInsets.all(2),
            child: Row(
              children: [
                _subTabButton(
                  index: 0,
                  label: 'Audit Report',
                  icon: Icons.assignment_turned_in_rounded,
                ),
                _subTabButton(
                  index: 1,
                  label: 'Revision Diff ($diffCount)',
                  icon: Icons.compare_arrows_rounded,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _subTabButton({
    required int index,
    required String label,
    required IconData icon,
  }) {
    final isSelected = _selectedSubTab == index;
    final theme = Theme.of(context);

    return InkWell(
      onTap: () => setState(() => _selectedSubTab = index),
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
        decoration: BoxDecoration(
          color: isSelected
              ? theme.colorScheme.primary.withAlpha(40)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: isSelected
              ? Border.all(
                  color: theme.colorScheme.primary.withAlpha(120),
                  width: 1,
                )
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 12,
              color: isSelected
                  ? theme.colorScheme.primary
                  : theme.colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                color: isSelected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Sub-Tab 0: Code Reviewer & Security Audit Report
  // ---------------------------------------------------------------------------
  Widget _buildReviewReportTab(
      BuildContext context, ReviewReportState reviewState, bool isDark) {
    final theme = Theme.of(context);

    if (reviewState.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest.withAlpha(80),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.verified_user_outlined,
                size: 48,
                color: theme.colorScheme.onSurfaceVariant.withAlpha(100),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Belum Ada Laporan Audit',
              style: GoogleFonts.inter(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Laporan audit kualitas, kepatuhan arsitektur, dan sertifikasi keamanan\nakan diterbitkan oleh Code Reviewer setelah seluruh pengujian selesai.',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                fontSize: 12,
                color: theme.colorScheme.onSurfaceVariant,
                height: 1.5,
              ),
            ),
          ],
        ),
      );
    }

    final isApproved = reviewState.isApproved;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Executive Summary Banner
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: isApproved
                    ? (isDark
                        ? [
                            const Color(0xFF10B981).withAlpha(30),
                            const Color(0xFF0F172A),
                          ]
                        : [
                            const Color(0xFFD1FAE5),
                            const Color(0xFFF8FAFC),
                          ])
                    : (isDark
                        ? [
                            const Color(0xFFF59E0B).withAlpha(30),
                            const Color(0xFF0F172A),
                          ]
                        : [
                            const Color(0xFFFEF3C7),
                            const Color(0xFFF8FAFC),
                          ]),
              ),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: isApproved
                    ? const Color(0xFF10B981).withAlpha(100)
                    : const Color(0xFFF59E0B).withAlpha(100),
                width: 1.2,
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: isApproved
                        ? const Color(0xFF10B981).withAlpha(40)
                        : const Color(0xFFF59E0B).withAlpha(40),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    isApproved ? Icons.verified_rounded : Icons.warning_amber_rounded,
                    color: isApproved ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                    size: 28,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isApproved
                            ? 'Code Reviewer & Quality Certification'
                            : 'Code Reviewer Audit: Perlu Revisi',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: theme.colorScheme.onSurface,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        isApproved
                            ? 'Seluruh implementasi telah diaudit terhadap standar modularitas, kebersihan kode, dan penanganan edge-cases.'
                            : 'Implementasi kode memerlukan perbaikan sesuai temuan audit sebelum dapat disetujui untuk rilis.',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: isApproved ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        isApproved ? '[APPROVED]' : '[NEEDS_REVISION]',
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest.withAlpha(140),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: theme.colorScheme.outline.withAlpha(60),
                          width: 0.8,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.repeat_rounded,
                            size: 11,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            reviewState.iteration > 0
                                ? "Loop: ${reviewState.iteration}/${reviewState.maxIterations}"
                                : "Loop: 0/${reviewState.maxIterations} (First-Pass)",
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Audit Report Content Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
                width: 1,
              ),
            ),
            child: MarkdownBody(
              data: reviewState.report,
              selectable: true,
              styleSheet: MarkdownStyleSheet(
                p: GoogleFonts.inter(
                  fontSize: 13,
                  height: 1.6,
                  color: theme.colorScheme.onSurface,
                ),
                h1: GoogleFonts.inter(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: theme.colorScheme.primary,
                ),
                h2: GoogleFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.onSurface,
                ),
                h3: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.onSurface,
                ),
                strong: GoogleFonts.inter(
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.onSurface,
                ),
                code: GoogleFonts.jetBrainsMono(
                  fontSize: 12,
                  backgroundColor: isDark
                      ? const Color(0xFF1E2230)
                      : const Color(0xFFE2E8F0),
                  color: isDark
                      ? const Color(0xFF38BDF8)
                      : const Color(0xFF0284C7),
                ),
                codeblockDecoration: BoxDecoration(
                  color: isDark
                      ? const Color(0xFF0D0E14)
                      : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isDark
                        ? const Color(0xFF2E3346)
                        : const Color(0xFFCBD5E1),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Sub-Tab 1: Revision Diff History
  // ---------------------------------------------------------------------------
  Widget _buildDiffHistoryTab(BuildContext context, List<DiffEntry> diffs,
      ReviewReportState reviewState, bool isDark) {
    final theme = Theme.of(context);

    // If there are diff entries from self-healing iterations:
    if (diffs.isNotEmpty) {
      return const DiffViewer();
    }

    // If no self-healing occurred, but the mission has finished successfully:
    if (!reviewState.isEmpty) {
      return Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 540),
          margin: const EdgeInsets.all(24),
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: const Color(0xFF10B981).withAlpha(90),
              width: 1.2,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withAlpha(35),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.check_circle_outline_rounded,
                  size: 48,
                  color: Color(0xFF10B981),
                ),
              ),
              const SizedBox(height: 18),
              Text(
                'First-Pass Quality (Zero Regression)',
                style: GoogleFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Seluruh automated unit test langsung lulus 100% pada siklus pertama.\nDeveloper Agent tidak memerlukan siklus perbaikan kode (Self-Healing Loop).',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: theme.colorScheme.onSurfaceVariant,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withAlpha(25),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: const Color(0xFF10B981).withAlpha(80),
                  ),
                ),
                child: Text(
                  '0 File Revisions Needed • Clean Architecture',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFF10B981),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Idle state before mission deployment
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.compare_rounded,
            size: 48,
            color: theme.colorScheme.onSurfaceVariant.withAlpha(100),
          ),
          const SizedBox(height: 16),
          Text(
            'Belum Ada Riwayat Revisi',
            style: GoogleFonts.inter(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: theme.colorScheme.onSurface,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Diff perbaikan kode akan muncul saat Developer melakukan\nself-healing setelah QA Tester mendeteksi kegagalan pada unit test.',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              fontSize: 12,
              color: theme.colorScheme.onSurfaceVariant,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}
