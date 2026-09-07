import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'widgets/app_header.dart';
import 'widgets/control_panel.dart';
import 'widgets/workspace_panel.dart';

class StudioScreen extends ConsumerWidget {
  const StudioScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: const AppHeader(),
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 800;

          if (isCompact) {
            // Layout vertikal/drawer untuk layar kecil
            return const Row(
              children: [
                Expanded(child: WorkspacePanel()),
              ],
            );
          }

          // Desktop Studio 3-Panel Responsive Layout
          return const Row(
            children: [
              // Left Control Hub Panel (330px)
              ControlPanel(),

              // Center & Right Main Workspace (Flexible)
              Expanded(
                child: WorkspacePanel(),
              ),
            ],
          );
        },
      ),
    );
  }
}