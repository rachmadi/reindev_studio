import 'package:flutter/material.dart';

enum AgentRole {
  productManager,
  systemArchitect,
  developer,
  qaTester,
  codeReviewer;

  String get id {
    switch (this) {
      case AgentRole.productManager:
        return 'pm';
      case AgentRole.systemArchitect:
        return 'architect';
      case AgentRole.developer:
        return 'developer';
      case AgentRole.qaTester:
        return 'tester';
      case AgentRole.codeReviewer:
        return 'reviewer';
    }
  }

  String get displayName {
    switch (this) {
      case AgentRole.productManager:
        return 'Product Manager';
      case AgentRole.systemArchitect:
        return 'System Architect';
      case AgentRole.developer:
        return 'Developer';
      case AgentRole.qaTester:
        return 'QA Tester';
      case AgentRole.codeReviewer:
        return 'Code Reviewer';
    }
  }

  String get subtitle {
    switch (this) {
      case AgentRole.productManager:
        return 'Prinsip SMART & User Story';
      case AgentRole.systemArchitect:
        return 'Modular File Tree & Contracts';
      case AgentRole.developer:
        return 'Code Synthesizer & Sanitizer';
      case AgentRole.qaTester:
        return 'Automated Tests & Assertions';
      case AgentRole.codeReviewer:
        return 'Security & Architecture Audit';
    }
  }

  IconData get icon {
    switch (this) {
      case AgentRole.productManager:
        return Icons.assignment_outlined;
      case AgentRole.systemArchitect:
        return Icons.account_tree_outlined;
      case AgentRole.developer:
        return Icons.code_rounded;
      case AgentRole.qaTester:
        return Icons.biotech_outlined;
      case AgentRole.codeReviewer:
        return Icons.verified_user_outlined;
    }
  }

  Color get accentColor {
    switch (this) {
      case AgentRole.productManager:
        return const Color(0xFF3B82F6); // Blue
      case AgentRole.systemArchitect:
        return const Color(0xFF8B5CF6); // Purple
      case AgentRole.developer:
        return const Color(0xFF10B981); // Emerald
      case AgentRole.qaTester:
        return const Color(0xFFF59E0B); // Amber
      case AgentRole.codeReviewer:
        return const Color(0xFF06B6D4); // Cyan
    }
  }

  static AgentRole? fromId(String id) {
    switch (id.toLowerCase()) {
      case 'pm':
      case 'product_manager':
      case 'product manager':
        return AgentRole.productManager;
      case 'architect':
      case 'system_architect':
      case 'system architect':
        return AgentRole.systemArchitect;
      case 'dev':
      case 'developer':
        return AgentRole.developer;
      case 'tester':
      case 'qa':
      case 'qa_tester':
      case 'qa tester':
      case 'executor':
        return AgentRole.qaTester;
      case 'reviewer':
      case 'code_reviewer':
      case 'code reviewer':
        return AgentRole.codeReviewer;
      default:
        return null;
    }
  }
}

enum AgentCardState {
  idle,
  thinking,
  working,
  testing,
  reviewing,
  retrying,
  completed,
  error;

  bool get isActive =>
      this == AgentCardState.thinking ||
      this == AgentCardState.working ||
      this == AgentCardState.testing ||
      this == AgentCardState.reviewing ||
      this == AgentCardState.retrying;

  String get label {
    switch (this) {
      case AgentCardState.idle:
        return 'Ready';
      case AgentCardState.thinking:
        return 'Thinking...';
      case AgentCardState.working:
        return 'Synthesizing...';
      case AgentCardState.testing:
        return 'Testing...';
      case AgentCardState.reviewing:
        return 'Reviewing...';
      case AgentCardState.retrying:
        return 'Self-Healing...';
      case AgentCardState.completed:
        return 'Completed';
      case AgentCardState.error:
        return 'Failed';
    }
  }

  Color getBadgeColor(ThemeData theme) {
    switch (this) {
      case AgentCardState.idle:
        return theme.colorScheme.onSurfaceVariant.withAlpha(120);
      case AgentCardState.thinking:
        return const Color(0xFF3B82F6);
      case AgentCardState.working:
        return const Color(0xFF10B981);
      case AgentCardState.testing:
        return const Color(0xFFF59E0B);
      case AgentCardState.reviewing:
        return const Color(0xFF8B5CF6);
      case AgentCardState.retrying:
        return const Color(0xFFEF4444);
      case AgentCardState.completed:
        return const Color(0xFF10B981);
      case AgentCardState.error:
        return const Color(0xFFEF4444);
    }
  }
}

class AgentCardStatus {
  final AgentRole role;
  final AgentCardState state;
  final String statusText;
  final int iteration;
  final DateTime? lastUpdated;

  const AgentCardStatus({
    required this.role,
    this.state = AgentCardState.idle,
    this.statusText = 'Ready',
    this.iteration = 0,
    this.lastUpdated,
  });

  AgentCardStatus copyWith({
    AgentCardState? state,
    String? statusText,
    int? iteration,
    DateTime? lastUpdated,
  }) {
    return AgentCardStatus(
      role: role,
      state: state ?? this.state,
      statusText: statusText ?? this.statusText,
      iteration: iteration ?? this.iteration,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }
}

class ThoughtItem {
  final String id;
  final DateTime timestamp;
  final AgentRole agentRole;
  final String title;
  final String content;
  final String type; // 'thought', 'code', 'test', 'review', 'system', 'error'
  final bool isCollapsible;
  final bool isExpanded;

  const ThoughtItem({
    required this.id,
    required this.timestamp,
    required this.agentRole,
    required this.title,
    required this.content,
    this.type = 'thought',
    this.isCollapsible = false,
    this.isExpanded = true,
  });

  ThoughtItem copyWith({
    bool? isExpanded,
  }) {
    return ThoughtItem(
      id: id,
      timestamp: timestamp,
      agentRole: agentRole,
      title: title,
      content: content,
      type: type,
      isCollapsible: isCollapsible,
      isExpanded: isExpanded ?? this.isExpanded,
    );
  }
}
