import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../models/agent_event.dart';
import '../../providers/squad_pipeline_provider.dart';

class AgentCardsRow extends ConsumerStatefulWidget {
  const AgentCardsRow({super.key});

  @override
  ConsumerState<AgentCardsRow> createState() => _AgentCardsRowState();
}

class _AgentCardsRowState extends ConsumerState<AgentCardsRow>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );

    _pulseAnimation = CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final activeRole = ref.watch(activeAgentRoleProvider);
    final agentStatuses = ref.watch(agentStatusesProvider);
    final currentFilter = ref.watch(streamFilterProvider);
    final loopState = ref.watch(loopStatusProvider);

    ref.listen<AgentRole?>(activeAgentRoleProvider, (previous, next) {
      if (next != null) {
        if (!_pulseController.isAnimating) {
          _pulseController.repeat(reverse: true);
        }
      } else {
        if (_pulseController.isAnimating) {
          _pulseController.stop();
          _pulseController.reset();
        }
      }
    });

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Icon(
                  Icons.device_hub_rounded,
                  size: 20,
                  color: theme.colorScheme.primary,
                ),
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
                const SizedBox(width: 10),
                // Dynamic Loop Counter Badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: loopState.currentLoop > 0
                        ? (loopState.isMaxReached
                            ? const Color(0xFFEF4444).withAlpha(35)
                            : const Color(0xFFF59E0B).withAlpha(35))
                        : theme.colorScheme.primary.withAlpha(25),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: loopState.currentLoop > 0
                          ? (loopState.isMaxReached
                              ? const Color(0xFFEF4444).withAlpha(120)
                              : const Color(0xFFF59E0B).withAlpha(120))
                          : theme.colorScheme.primary.withAlpha(80),
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.repeat_rounded,
                        size: 11,
                        color: loopState.currentLoop > 0
                            ? (loopState.isMaxReached
                                ? const Color(0xFFEF4444)
                                : const Color(0xFFF59E0B))
                            : theme.colorScheme.primary,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        loopState.currentLoop > 0
                            ? "Loop ${loopState.currentLoop}/${loopState.maxLoops}"
                            : "Loop 0/${loopState.maxLoops}",
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: loopState.currentLoop > 0
                              ? (loopState.isMaxReached
                                  ? const Color(0xFFEF4444)
                                  : const Color(0xFFF59E0B))
                              : theme.colorScheme.primary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (currentFilter != null)
              InkWell(
                onTap: () => ref.read(streamFilterProvider.notifier).setFilter(null),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.filter_alt_off_rounded, size: 14, color: theme.colorScheme.primary),
                      const SizedBox(width: 4),
                      Text(
                        "Reset Filter: ${currentFilter.displayName}",
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
          ],
        ),
        const SizedBox(height: 14),
        LayoutBuilder(
          builder: (context, constraints) {
            final cardWidth = (constraints.maxWidth - (4 * 10)) / 5;
            final isVeryNarrow = cardWidth < 140;

            if (isVeryNarrow) {
              return Wrap(
                spacing: 8,
                runSpacing: 8,
                children: AgentRole.values.map((role) {
                  return SizedBox(
                    width: (constraints.maxWidth - 8) / 2,
                    child: _buildCard(
                      context: context,
                      role: role,
                      status: agentStatuses[role] ??
                          AgentCardStatus(role: role, state: AgentCardState.idle),
                      isActive: activeRole == role,
                      isSelected: currentFilter == role,
                    ),
                  );
                }).toList(),
              );
            }

            return Row(
              children: AgentRole.values.map((role) {
                return Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 5),
                    child: _buildCard(
                      context: context,
                      role: role,
                      status: agentStatuses[role] ??
                          AgentCardStatus(role: role, state: AgentCardState.idle),
                      isActive: activeRole == role,
                      isSelected: currentFilter == role,
                    ),
                  ),
                );
              }).toList(),
            );
          },
        ),
      ],
    );
  }

  Widget _buildCard({
    required BuildContext context,
    required AgentRole role,
    required AgentCardStatus status,
    required bool isActive,
    required bool isSelected,
  }) {
    final theme = Theme.of(context);
    final cardColor = theme.colorScheme.surfaceContainerHighest.withAlpha(90);

    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        final glowOpacity = isActive ? (_pulseAnimation.value * 0.5 + 0.3) : 0.0;
        final borderGlowColor = isActive
            ? role.accentColor.withValues(alpha: glowOpacity)
            : isSelected
                ? theme.colorScheme.primary
                : theme.colorScheme.outline.withAlpha(40);

        return InkWell(
          onTap: () {
            // Toggle filter stream by clicking agent card
            final current = ref.read(streamFilterProvider);
            if (current == role) {
              ref.read(streamFilterProvider.notifier).setFilter(null);
            } else {
              ref.read(streamFilterProvider.notifier).setFilter(role);
            }
          },
          borderRadius: BorderRadius.circular(12),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: cardColor,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: borderGlowColor,
                width: isActive ? 1.8 : 1.0,
              ),
              boxShadow: isActive
                  ? [
                      BoxShadow(
                        color: role.accentColor.withValues(alpha: glowOpacity * 0.4),
                        blurRadius: 10 + (_pulseAnimation.value * 6),
                        spreadRadius: 1 + (_pulseAnimation.value * 2),
                      ),
                    ]
                  : null,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // Top row: Icon + Status indicator dot
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: role.accentColor.withAlpha(isActive ? 60 : 35),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(
                        role.icon,
                        size: 16,
                        color: role.accentColor,
                      ),
                    ),
                    // Status Dot Indicator (Pulsing if active)
                    _buildDotIndicator(theme, role, status.state, isActive),
                  ],
                ),
                const SizedBox(height: 10),

                // Role Name
                Text(
                  role.displayName,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.onSurface,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),

                // Subtitle
                Text(
                  role.subtitle,
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    color: theme.colorScheme.onSurfaceVariant.withAlpha(160),
                  ),
                  overflow: TextOverflow.ellipsis,
                  maxLines: 1,
                ),
                const SizedBox(height: 10),

                // Dynamic Status Badge (REQ-023)
                _buildStatusBadge(theme, role, status, isActive),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildDotIndicator(
      ThemeData theme, AgentRole role, AgentCardState state, bool isActive) {
    if (isActive) {
      return Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: role.accentColor,
          boxShadow: [
            BoxShadow(
              color: role.accentColor.withValues(alpha: _pulseAnimation.value * 0.8),
              blurRadius: 6,
              spreadRadius: 2,
            ),
          ],
        ),
      );
    }

    Color dotColor = const Color(0xFF6B7280); // Idle grey
    if (state == AgentCardState.completed) {
      dotColor = const Color(0xFF10B981); // Green
    } else if (state == AgentCardState.retrying || state == AgentCardState.error) {
      dotColor = const Color(0xFFEF4444); // Red
    }

    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: dotColor,
      ),
    );
  }

  Widget _buildStatusBadge(ThemeData theme, AgentRole role,
      AgentCardStatus status, bool isActive) {
    Color badgeBg;
    Color badgeTextColor;
    String label = status.statusText;

    if (isActive) {
      badgeBg = role.accentColor.withAlpha(50);
      badgeTextColor = role.accentColor;
    } else {
      switch (status.state) {
        case AgentCardState.completed:
          badgeBg = const Color(0xFF10B981).withAlpha(40);
          badgeTextColor = const Color(0xFF10B981);
          break;
        case AgentCardState.retrying:
        case AgentCardState.error:
          badgeBg = const Color(0xFFEF4444).withAlpha(40);
          badgeTextColor = const Color(0xFFEF4444);
          break;
        case AgentCardState.idle:
        default:
          badgeBg = theme.colorScheme.surfaceContainerHighest.withAlpha(120);
          badgeTextColor = theme.colorScheme.onSurfaceVariant.withAlpha(150);
          label = "Ready";
          break;
      }
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: badgeBg,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: badgeTextColor.withAlpha(80),
          width: 0.8,
        ),
      ),
      child: Text(
        label,
        style: GoogleFonts.jetBrainsMono(
          fontSize: 9.5,
          fontWeight: FontWeight.w700,
          color: badgeTextColor,
        ),
        overflow: TextOverflow.ellipsis,
        textAlign: TextAlign.center,
      ),
    );
  }
}
