import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/settings_service.dart';
import '../services/n8n_webhook_service.dart';
import '../theme/cyberpunk_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _webhookUrlController;
  bool _isTesting = false;

  static const List<String> _supportedLanguages = [
    'Czech',
    'English',
    'German',
    'French',
    'Spanish',
    'Italian',
    'Polish',
    'Slovak',
    'Ukrainian',
  ];

  @override
  void initState() {
    super.initState();
    final settings = context.read<SettingsService>();
    _webhookUrlController = TextEditingController(text: settings.webhookUrl);
  }

  @override
  void dispose() {
    _webhookUrlController.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    setState(() => _isTesting = true);
    try {
      final n8nService = context.read<N8nWebhookService>();
      n8nService.setBaseUrl(_webhookUrlController.text);
      final success = await n8nService.testConnection();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(success ? 'Connection successful!' : 'Connection failed.'),
          backgroundColor: success ? Colors.green.shade700 : Colors.red.shade700,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Connection error: $e'),
          backgroundColor: Colors.red.shade700,
        ));
      }
    } finally {
      setState(() => _isTesting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsService>();

    return Scaffold(
      backgroundColor: const Color(0xFF0D0D1A),
      appBar: AppBar(
        title: const Text('Settings'),
        backgroundColor: const Color(0xFF1A1A2E),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader('Connection'),
            const SizedBox(height: 12),
            _buildConnectionSection(settings),
            const SizedBox(height: 24),
            _buildSectionHeader('Language'),
            const SizedBox(height: 12),
            _buildLanguageSection(settings),
            const SizedBox(height: 24),
            _buildSectionHeader('Mesh'),
            const SizedBox(height: 12),
            _buildMeshSection(settings),
            const SizedBox(height: 24),
            _buildSectionHeader('About'),
            const SizedBox(height: 12),
            _buildAboutSection(settings),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(color: Colors.cyanAccent, fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 1.2),
    );
  }

  Widget _buildConnectionSection(SettingsService settings) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: const Color(0xFF1E1E2E), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('n8n Webhook URL', style: TextStyle(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 8),
          TextField(
            controller: _webhookUrlController,
            decoration: InputDecoration(
              hintText: 'https://your-n8n.example.com/webhook/...',
              hintStyle: const TextStyle(color: Colors.white24),
              enabledBorder: const OutlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
              focusedBorder: const OutlineInputBorder(borderSide: BorderSide(color: Colors.cyanAccent)),
              suffixIcon: IconButton(
                icon: _isTesting
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.cyanAccent))
                    : const Icon(Icons.wifi_tethering, color: Colors.cyanAccent),
                onPressed: _isTesting ? null : _testConnection,
                tooltip: 'Test Connection',
              ),
            ),
            style: const TextStyle(color: Colors.white, fontSize: 13),
            onChanged: (value) => settings.setWebhookUrl(value),
          ),
        ],
      ),
    );
  }

  Widget _buildLanguageSection(SettingsService settings) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: const Color(0xFF1E1E2E), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Default Language', style: TextStyle(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: settings.defaultLanguage,
            dropdownColor: const Color(0xFF2A2A3E),
            decoration: const InputDecoration(
              enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
              focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.cyanAccent)),
            ),
            style: const TextStyle(color: Colors.white),
            items: _supportedLanguages.map((lang) => DropdownMenuItem(value: lang, child: Text(lang))).toList(),
            onChanged: (value) {
              if (value != null) settings.setDefaultLanguage(value);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildMeshSection(SettingsService settings) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: const Color(0xFF1E1E2E), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Daemon Enabled', style: TextStyle(color: Colors.white, fontSize: 14)),
              Switch(
                value: settings.meshDaemonEnabled,
                onChanged: (v) => settings.setMeshDaemonEnabled(v),
                activeColor: Colors.cyanAccent,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text('Max CPU Share: ${settings.maxCpuShare.toInt()}%', style: const TextStyle(color: Colors.white70, fontSize: 13)),
          Slider(
            value: settings.maxCpuShare,
            min: 10,
            max: 90,
            divisions: 16,
            activeColor: Colors.cyanAccent,
            inactiveColor: Colors.white12,
            label: '${settings.maxCpuShare.toInt()}%',
            onChanged: (v) => settings.setMaxCpuShare(v),
          ),
          const SizedBox(height: 12),
          Text('Max RAM Share: ${settings.maxRamShare.toInt()} MB', style: const TextStyle(color: Colors.white70, fontSize: 13)),
          Slider(
            value: settings.maxRamShare,
            min: 256,
            max: 4096,
            divisions: 15,
            activeColor: Colors.cyanAccent,
            inactiveColor: Colors.white12,
            label: '${settings.maxRamShare.toInt()} MB',
            onChanged: (v) => settings.setMaxRamShare(v),
          ),
        ],
      ),
    );
  }

  Widget _buildAboutSection(SettingsService settings) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: const Color(0xFF1E1E2E), borderRadius: BorderRadius.circular(12)),
      child: Column(
        children: [
          _buildAboutRow('App Version', settings.appVersion),
          const Divider(color: Colors.white12, height: 20),
          _buildAboutRow('Ada/SPARK Binary', settings.adaSparkBinaryPath),
          const Divider(color: Colors.white12, height: 20),
          _buildAboutRow('Project', 'Asgard Mesh Client'),
          const Divider(color: Colors.white12, height: 20),
          _buildAboutRow('License', 'MIT'),
        ],
      ),
    );
  }

  Widget _buildAboutRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: Colors.white70, fontSize: 13)),
        Flexible(child: Text(value, style: const TextStyle(color: Colors.white, fontSize: 13), textAlign: TextAlign.end, overflow: TextOverflow.ellipsis)),
      ],
    );
  }
}
