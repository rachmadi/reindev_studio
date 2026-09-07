import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/app_providers.dart';

class EngineModelInfo {
  final String id;
  final String label;
  final String description;
  final bool isLocal;

  const EngineModelInfo({
    required this.id,
    required this.label,
    required this.description,
    required this.isLocal,
  });
}

class EngineSelector extends ConsumerWidget {
  const EngineSelector({super.key});

  static const List<EngineModelInfo> availableEngines = [
    EngineModelInfo(
      id: "Ollama (qwen2.5-coder:7b)",
      label: "Ollama (qwen2.5-coder:7b)",
      description: "Resident 6GB VRAM • Offline Bebas Biaya",
      isLocal: true,
    ),
    EngineModelInfo(
      id: "Gemini 2.0 Flash (Cloud)",
      label: "Gemini 2.0 Flash (Cloud)",
      description: "OpenRouter • Ultra Fast & 1M Context",
      isLocal: false,
    ),
    EngineModelInfo(
      id: "Claude 3.5 Sonnet (Cloud)",
      label: "Claude 3.5 Sonnet (Cloud)",
      description: "OpenRouter • SOTA Code Generation",
      isLocal: false,
    ),
    EngineModelInfo(
      id: "Qwen 2.5 Coder 32B (Cloud)",
      label: "Qwen 2.5 Coder 32B (Cloud)",
      description: "OpenRouter • Dense Reasoning Model",
      isLocal: false,
    ),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final activeEngine = ref.watch(activeEngineProvider);

    final selectedInfo = availableEngines.firstWhere(
      (e) => e.id == activeEngine,
      orElse: () => availableEngines.first,
    );

    return Card(
      elevation: 0,
      color: theme.colorScheme.surfaceContainerHighest.withAlpha(90),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: theme.colorScheme.outline.withAlpha(50),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  selectedInfo.isLocal
                      ? Icons.memory_rounded
                      : Icons.cloud_queue_rounded,
                  size: 16,
                  color: selectedInfo.isLocal
                      ? const Color(0xFF10B981)
                      : theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(
                    color: selectedInfo.isLocal
                        ? const Color(0xFF10B981).withAlpha(40)
                        : theme.colorScheme.primary.withAlpha(40),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    selectedInfo.isLocal ? "LOCAL RESIDENT" : "CLOUD OPENROUTER",
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: selectedInfo.isLocal
                          ? const Color(0xFF10B981)
                          : theme.colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: selectedInfo.isLocal
                        ? Colors.amber.withAlpha(35)
                        : Colors.purple.withAlpha(35),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: selectedInfo.isLocal
                          ? Colors.amber.withAlpha(80)
                          : Colors.purple.withAlpha(80),
                      width: 0.8,
                    ),
                  ),
                  child: Text(
                    selectedInfo.isLocal ? "⚡ Fast" : "✨ High Accuracy",
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: selectedInfo.isLocal
                          ? Colors.amber
                          : const Color(0xFFA855F7),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: availableEngines.any((e) => e.id == activeEngine)
                    ? activeEngine
                    : availableEngines.first.id,
                isExpanded: true,
                icon: const Icon(Icons.arrow_drop_down_rounded, size: 20),
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: theme.colorScheme.onSurface,
                ),
                dropdownColor: theme.colorScheme.surfaceContainerHigh,
                items: availableEngines.map((engine) {
                  return DropdownMenuItem<String>(
                    value: engine.id,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          engine.label,
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          engine.description,
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 9,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (String? newEngine) {
                  if (newEngine != null) {
                    ref.read(activeEngineProvider.notifier).setEngine(newEngine);
                  }
                },
              ),
            ),
            const SizedBox(height: 6),
            // Chip Penjelas Performa Engine (REQ-020)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(
                color: selectedInfo.isLocal
                    ? const Color(0xFF10B981).withAlpha(25)
                    : theme.colorScheme.primary.withAlpha(25),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(
                  color: selectedInfo.isLocal
                      ? const Color(0xFF10B981).withAlpha(60)
                      : theme.colorScheme.primary.withAlpha(60),
                  width: 0.8,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    selectedInfo.isLocal
                        ? Icons.bolt_rounded
                        : Icons.auto_awesome_rounded,
                    size: 13,
                    color: selectedInfo.isLocal
                        ? const Color(0xFF10B981)
                        : theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      selectedInfo.isLocal
                          ? "Fast • Resident 6GB (Offline Bebas Biaya)"
                          : "High Accuracy • Cloud API (OpenRouter)",
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: selectedInfo.isLocal
                            ? const Color(0xFF10B981)
                            : theme.colorScheme.primary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
