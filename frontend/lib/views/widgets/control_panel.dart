import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/app_providers.dart';
import '../../providers/squad_pipeline_provider.dart';
import 'engine_selector.dart';

class ControlPanel extends ConsumerStatefulWidget {
  const ControlPanel({super.key});

  @override
  ConsumerState<ControlPanel> createState() => _ControlPanelState();
}

class _ControlPanelState extends ConsumerState<ControlPanel> {
  late TextEditingController _promptController;
  String? _errorMessage;

  static const Map<String, String> presets = {
    "FastAPI CRUD":
        "Bangun modul REST API FastAPI untuk manajemen inventaris produk dengan validasi Pydantic dan automated pytest.",
    "Flutter Widget":
        "Bangun komponen widget kartu metrik modern responsif Flutter dengan Material Design 3 dan Riverpod state.",
    "CLI Calculator":
        "Bangun kalkulator CLI Python dengan operasi matematika matriks dan penanganan error komprehensif.",
  };

  @override
  void initState() {
    super.initState();
    _promptController = TextEditingController(
      text: ref.read(promptInputProvider),
    );
  }

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  void _applyPreset(String label, String text) {
    setState(() {
      _promptController.text = text;
      _errorMessage = null;
    });
    ref.read(promptInputProvider.notifier).setPrompt(text);
    if (label.contains("Flutter")) {
      ref.read(targetLanguageProvider.notifier).setLanguage("Dart / Flutter");
    } else {
      ref.read(targetLanguageProvider.notifier).setLanguage("Python");
    }
  }

  void _handleDeploy() {
    final text = _promptController.text.trim();
    if (text.isEmpty) {
      setState(() {
        _errorMessage = "Deskripsi misi tidak boleh kosong.";
      });
      return;
    }

    setState(() {
      _errorMessage = null;
    });

    ref.read(promptInputProvider.notifier).setPrompt(text);
    ref.read(isDeployingProvider.notifier).setDeploying(true);
    ref.read(squadStatusProvider.notifier).setStatus("deploying");

    // Beralih ke tab 0 (Agent Squad Timeline) agar pengguna melihat progres langsung
    ref.read(activeWorkspaceTabProvider.notifier).setTab(0);

    final activeEngine = ref.read(activeEngineProvider);
    var targetLang = ref.read(targetLanguageProvider);

    // Auto-align bahasa target jika prompt secara eksplisit merujuk ke Flutter / Dart
    final lowerText = text.toLowerCase();
    if (lowerText.contains("flutter") ||
        lowerText.contains("widget") ||
        lowerText.contains("dart")) {
      if (!targetLang.toLowerCase().contains("dart") &&
          !targetLang.toLowerCase().contains("flutter")) {
        targetLang = "Dart / Flutter";
        ref.read(targetLanguageProvider.notifier).setLanguage("Dart / Flutter");
      }
    }

    final maxLoops = ref.read(maxQaLoopsProvider);
    final executorIntervention = ref.read(executorInterventionProvider);
    final executorMode = ref.read(executorModeProvider);

    // Memicu pipeline squad via Pipeline Coordinator (WebSocket & Responsive Stream)
    ref.read(pipelineCoordinatorProvider).deploy(
          task: text,
          provider: activeEngine.toLowerCase().contains("cloud")
              ? "openrouter"
              : "ollama",
          modelName: activeEngine,
          targetLanguage: targetLang,
          maxIterations: maxLoops,
          executorInterventionEnabled: executorIntervention,
          executorMode: executorMode,
        );


    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          "Squad otonom berhasil dideploy! Aliran pemikiran agen disiarkan...",
          style: GoogleFonts.inter(fontSize: 12),
        ),
        backgroundColor: const Color(0xFF10B981),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final maxLoops = ref.watch(maxQaLoopsProvider);
    final targetLang = ref.watch(targetLanguageProvider);
    final executorIntervention = ref.watch(executorInterventionProvider);
    final executorMode = ref.watch(executorModeProvider);
    final isDeploying = ref.watch(isDeployingProvider);
    final missionDuration = ref.watch(missionDurationProvider);
    final squadStatus = ref.watch(squadStatusProvider);

    return Container(
      width: 330,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          right: BorderSide(
            color: theme.dividerTheme.color ?? theme.colorScheme.outlineVariant,
            width: 1,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Control Panel
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  Icons.tune_rounded,
                  size: 20,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    "Mission Control Hub",
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
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withAlpha(40),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    "Active",
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFF10B981),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Scrollable Body
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // 1. Mission Intent Specification (REQ-019)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      "MISSION INTENT",
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: theme.colorScheme.onSurfaceVariant,
                        letterSpacing: 0.8,
                      ),
                    ),
                    if (_promptController.text.isNotEmpty)
                      InkWell(
                        borderRadius: BorderRadius.circular(4),
                        onTap: () {
                          setState(() {
                            _promptController.clear();
                            _errorMessage = null;
                          });
                          ref.read(promptInputProvider.notifier).clear();
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.close_rounded, size: 13, color: theme.colorScheme.error),
                              const SizedBox(width: 2),
                              Text(
                                "Hapus",
                                style: GoogleFonts.inter(
                                  fontSize: 10,
                                  color: theme.colorScheme.error,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _promptController,
                  minLines: 3,
                  maxLines: 5,
                  maxLength: 1000,
                  style: GoogleFonts.inter(fontSize: 12, height: 1.4),
                  decoration: InputDecoration(
                    hintText:
                        "Spesifikasikan fitur, arsitektur, atau modul yang ingin dibangun squad...",
                    hintStyle: GoogleFonts.inter(
                      fontSize: 12,
                      color: theme.colorScheme.onSurfaceVariant.withAlpha(150),
                    ),
                    errorText: _errorMessage,
                    errorStyle: GoogleFonts.inter(fontSize: 11),
                    filled: true,
                    fillColor: theme.colorScheme.surfaceContainerHighest
                        .withAlpha(60),
                    contentPadding: const EdgeInsets.all(12),
                    suffixIcon: _promptController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.close_rounded, size: 18),
                            tooltip: "Hapus teks prompt (Clear)",
                            onPressed: () {
                              setState(() {
                                _promptController.clear();
                                _errorMessage = null;
                              });
                              ref.read(promptInputProvider.notifier).clear();
                            },
                          )
                        : null,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(
                        color: theme.colorScheme.outline.withAlpha(50),
                      ),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(
                        color: theme.colorScheme.outline.withAlpha(50),
                      ),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide(
                        color: theme.colorScheme.primary,
                        width: 1.5,
                      ),
                    ),
                  ),
                  onChanged: (val) {
                    setState(() {
                      if (_errorMessage != null && val.trim().isNotEmpty) {
                        _errorMessage = null;
                      }
                    });
                    ref.read(promptInputProvider.notifier).setPrompt(val);
                  },
                ),

                const SizedBox(height: 12),

                // Quick Presets (REQ-022)
                Text(
                  "PRESET MISI CEPAT",
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.onSurfaceVariant,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _presetChip(
                      context,
                      "FastAPI CRUD",
                      Icons.api_rounded,
                      presets["FastAPI CRUD"]!,
                    ),
                    _presetChip(
                      context,
                      "Flutter Widget",
                      Icons.widgets_rounded,
                      presets["Flutter Widget"]!,
                    ),
                    _presetChip(
                      context,
                      "CLI Calculator",
                      Icons.terminal_rounded,
                      presets["CLI Calculator"]!,
                    ),
                  ],
                ),

                const SizedBox(height: 20),

                // 2. Engine & Model Configuration (REQ-020)
                Text(
                  "AI ENGINE SPECIFICATION",
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.onSurfaceVariant,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),
                const EngineSelector(),

                const SizedBox(height: 20),

                // 3. Squad Tuning Parameters (REQ-021)
                Text(
                  "SQUAD TUNING",
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.onSurfaceVariant,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),
                Card(
                  elevation: 0,
                  color:
                      theme.colorScheme.surfaceContainerHighest.withAlpha(60),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                    side: BorderSide(
                      color: theme.colorScheme.outline.withAlpha(50),
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                "Max QA Loops (Self-Healing):",
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              "${maxLoops}x",
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: theme.colorScheme.primary,
                              ),
                            ),
                          ],
                        ),
                        SliderTheme(
                          data: SliderTheme.of(context).copyWith(
                            trackHeight: 3,
                            thumbShape: const RoundSliderThumbShape(
                                enabledThumbRadius: 7),
                          ),
                          child: Slider(
                            value: maxLoops.toDouble(),
                            min: 1,
                            max: 5,
                            divisions: 4,
                            label: "${maxLoops}x loops",
                            onChanged: (val) {
                              ref
                                  .read(maxQaLoopsProvider.notifier)
                                  .setLoops(val.round());
                            },
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          "Target Language / Stack:",
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: ChoiceChip(
                                label: Center(
                                  child: Text(
                                    "Python",
                                    style: GoogleFonts.inter(fontSize: 11),
                                  ),
                                ),
                                selected: targetLang == "Python",
                                onSelected: (sel) {
                                  if (sel) {
                                    ref
                                        .read(targetLanguageProvider.notifier)
                                        .setLanguage("Python");
                                  }
                                },
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: ChoiceChip(
                                label: Center(
                                  child: Text(
                                    "Dart / Flutter",
                                    style: GoogleFonts.inter(fontSize: 11),
                                  ),
                                ),
                                selected: targetLang.contains("Dart"),
                                onSelected: (sel) {
                                  if (sel) {
                                    ref
                                        .read(targetLanguageProvider.notifier)
                                        .setLanguage("Dart / Flutter");
                                  }
                                },
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Flexible(
                              child: Text(
                                "Executor Intervention Mode:",
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: executorMode == "ON"
                                    ? const Color(0xFF10B981).withAlpha(40)
                                    : (executorMode == "CODE_ONLY"
                                        ? const Color(0xFF06B6D4).withAlpha(40)
                                        : Colors.amber.withAlpha(40)),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                executorMode,
                                style: GoogleFonts.jetBrainsMono(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  color: executorMode == "ON"
                                      ? const Color(0xFF10B981)
                                      : (executorMode == "CODE_ONLY"
                                          ? const Color(0xFF06B6D4)
                                          : Colors.amber),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: ChoiceChip(
                                padding: EdgeInsets.zero,
                                labelPadding: const EdgeInsets.symmetric(horizontal: 2),
                                avatar: Icon(
                                  Icons.auto_fix_high_rounded,
                                  size: 13,
                                  color: executorMode == "ON"
                                      ? const Color(0xFF10B981)
                                      : theme.colorScheme.onSurfaceVariant,
                                ),
                                label: Center(
                                  child: Text(
                                    "ON",
                                    style: GoogleFonts.inter(fontSize: 11),
                                  ),
                                ),
                                selected: executorMode == "ON",
                                onSelected: (sel) {
                                  if (sel) {
                                    ref
                                        .read(
                                            executorModeProvider.notifier)
                                        .setMode("ON");
                                  }
                                },
                              ),
                            ),
                            const SizedBox(width: 4),
                             Expanded(
                              child: ChoiceChip(
                                padding: EdgeInsets.zero,
                                labelPadding: const EdgeInsets.symmetric(horizontal: 4),
                                label: Center(
                                  child: Text(
                                    "CODE",
                                    style: GoogleFonts.inter(
                                      fontSize: 11,
                                      color: executorMode == "CODE_ONLY"
                                          ? const Color(0xFF06B6D4)
                                          : null,
                                    ),
                                  ),
                                ),
                                selected: executorMode == "CODE_ONLY",
                                onSelected: (sel) {
                                  if (sel) {
                                    ref
                                        .read(
                                            executorModeProvider.notifier)
                                        .setMode("CODE_ONLY");
                                  }
                                },
                              ),
                            ),
                            const SizedBox(width: 4),
                            Expanded(
                              child: ChoiceChip(
                                padding: EdgeInsets.zero,
                                labelPadding: const EdgeInsets.symmetric(horizontal: 2),
                                avatar: Icon(
                                  Icons.block_rounded,
                                  size: 13,
                                  color: executorMode == "OFF"
                                      ? Colors.amber
                                      : theme.colorScheme.onSurfaceVariant,
                                ),
                                label: Center(
                                  child: Text(
                                    "OFF",
                                    style: GoogleFonts.inter(fontSize: 11),
                                  ),
                                ),
                                selected: executorMode == "OFF",
                                onSelected: (sel) {
                                  if (sel) {
                                    ref
                                        .read(
                                            executorModeProvider.notifier)
                                        .setMode("OFF");
                                  }
                                },
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          executorMode == "ON"
                              ? "Auto-healing & intervensi code + test aktif."
                              : (executorMode == "CODE_ONLY"
                                  ? "Intervensi hanya pada code; test DILARANG diubah."
                                  : "Pengujian artefak murni tanpa intervensi."),
                          style: GoogleFonts.inter(
                            fontSize: 10,
                            color: theme.colorScheme.onSurfaceVariant
                                .withAlpha(180),
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Bottom Action Button (Deploy Squad) (REQ-022)
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (missionDuration != null && squadStatus == 'completed') ...[
                  Container(
                    margin: const EdgeInsets.only(bottom: 10),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withAlpha(25),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF10B981).withAlpha(80)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.timer_rounded, size: 15, color: Color(0xFF10B981)),
                        const SizedBox(width: 6),
                        Text(
                          "Total Waktu: ${missionDuration.toStringAsFixed(1)}s",
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w700,
                            color: const Color(0xFF10B981),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                FilledButton.icon(
                  onPressed: isDeploying ? null : _handleDeploy,
                  icon: isDeploying
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.rocket_launch_rounded, size: 18),
                  label: Text(
                    isDeploying
                        ? "Deploying Squad..."
                        : "Deploy Autonomous Squad",
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _presetChip(
      BuildContext context, String label, IconData icon, String text) {
    final theme = Theme.of(context);
    return ActionChip(
      avatar: Icon(icon, size: 14, color: theme.colorScheme.primary),
      label: Text(
        label,
        style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w500),
      ),
      onPressed: () => _applyPreset(label, text),
    );
  }
}
