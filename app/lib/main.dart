import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'services/mesh_daemon_service.dart';
import 'services/n8n_webhook_service.dart';
import 'services/settings_service.dart';
import 'screens/app_shell.dart';
import 'theme/cyberpunk_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final settingsService = SettingsService();
  await settingsService.load();

  runApp(AsgardMeshApp(settingsService: settingsService));
}

class AsgardMeshApp extends StatelessWidget {
  final SettingsService settingsService;

  const AsgardMeshApp({super.key, required this.settingsService});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: settingsService),
        ChangeNotifierProvider(create: (_) => N8nWebhookService()),
        ChangeNotifierProxyProvider<N8nWebhookService, MeshDaemonService>(
          create: (context) => MeshDaemonService(
            context.read<N8nWebhookService>(),
          ),
          update: (_, webhook, previous) =>
              previous ?? MeshDaemonService(webhook),
        ),
      ],
      child: MaterialApp(
        title: 'Asgard Mesh Client',
        theme: CyberpunkTheme.darkTheme,
        home: const AppShell(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
