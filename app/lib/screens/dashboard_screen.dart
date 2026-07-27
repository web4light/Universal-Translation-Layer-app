import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/mesh_daemon_service.dart';
import '../services/n8n_webhook_service.dart';
import '../theme/cyberpunk_theme.dart';

/// System overview dashboard with cyberpunk-styled status cards.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isRefreshing = false;
  DateTime? _lastSyncTime;

  static const Color _cyan = Color(0xFF00F0FF);
  static const Color _gold = Color(0xFFFFB800);

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() => _isRefreshing = true);

    final meshService = context.read<MeshDaemonService>();
    final n8nService = context.read<N8nWebhookService>();

    await Future.wait([
      meshService.refreshStatus(),
      n8nService.testConnection(),
    ]);

    setState(() {
      _isRefreshing = false;
      _lastSyncTime = DateTime.now();
    });
  }

  @override
  Widget build(BuildContext context) {
    final meshService = context.watch<MeshDaemonService>();
    final n8nService = context.watch<N8nWebhookService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('ASGARD MESH — DASHBOARD'),
        actions: [
          IconButton(
            icon: _isRefreshing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: _cyan,
                    ),
                  )
                : const Icon(Icons.refresh, color: _cyan),
            onPressed: _isRefreshing ? null : _refresh,
            tooltip: 'Refresh Status',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Last sync time
            if (_lastSyncTime != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Row(
                  children: [
                    const Icon(Icons.sync, size: 14, color: Colors.white38),
                    const SizedBox(width: 6),
                    Text(
                      'Last sync: ${_formatTime(_lastSyncTime!)}',
                      style: const TextStyle(
                        color: Colors.white38,
                        fontSize: 12,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),

            // Status indicators section
            const _SectionHeader(title: 'SYSTEM STATUS'),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _StatusIndicatorCard(
                    label: 'Mesh',
                    isActive: meshService.isRunning,
                    activeText: 'Connected',
                    inactiveText: 'Disconnected',
                    icon: Icons.hub,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatusIndicatorCard(
                    label: 'n8n Webhook',
                    isActive: n8nService.isConnected,
                    activeText: 'Reachable',
                    inactiveText: 'Unreachable',
                    icon: Icons.webhook,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatusIndicatorCard(
                    label: 'Daemon',
                    isActive: meshService.isRunning,
                    activeText: 'Running',
                    inactiveText: 'Stopped',
                    icon: Icons.memory,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 28),

            // Stats cards section
            const _SectionHeader(title: 'NETWORK STATS'),
            const SizedBox(height: 12),
            GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.6,
              children: [
                _StatsCard(
                  label: 'Connected Peers',
                  value: '${meshService.connectedPeers}',
                  icon: Icons.people_outline,
                ),
                _StatsCard(
                  label: 'Tasks Processed',
                  value: '${meshService.totalTasksProcessed}',
                  icon: Icons.task_alt,
                ),
                _StatsCard(
                  label: 'Uptime',
                  value: _formatDuration(meshService.uptime),
                  icon: Icons.timer_outlined,
                ),
                _StatsCard(
                  label: 'CPU Contribution',
                  value: '${(meshService.cpuContribution * 100).toStringAsFixed(0)}%',
                  icon: Icons.developer_board,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:'
        '${time.minute.toString().padLeft(2, '0')}:'
        '${time.second.toString().padLeft(2, '0')}';
  }

  String _formatDuration(Duration d) {
    final hours = d.inHours;
    final minutes = d.inMinutes.remainder(60);
    final seconds = d.inSeconds.remainder(60);
    if (hours > 0) return '${hours}h ${minutes}m';
    if (minutes > 0) return '${minutes}m ${seconds}s';
    return '${seconds}s';
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;

  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(
        color: Color(0xFF00F0FF),
        fontSize: 13,
        fontWeight: FontWeight.w700,
        letterSpacing: 2.0,
        fontFamily: 'monospace',
      ),
    );
  }
}

class _StatusIndicatorCard extends StatelessWidget {
  final String label;
  final bool isActive;
  final String activeText;
  final String inactiveText;
  final IconData icon;

  static const Color _cyan = Color(0xFF00F0FF);

  const _StatusIndicatorCard({
    required this.label,
    required this.isActive,
    required this.activeText,
    required this.inactiveText,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = isActive ? Colors.greenAccent : Colors.redAccent;
    final statusText = isActive ? activeText : inactiveText;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black54,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _cyan.withOpacity(0.3), width: 1),
        boxShadow: [
          BoxShadow(
            color: _cyan.withOpacity(0.1),
            blurRadius: 8,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: _cyan, size: 22),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 11,
              fontFamily: 'monospace',
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: statusColor,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: statusColor.withOpacity(0.6),
                      blurRadius: 4,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Text(
                statusText,
                style: TextStyle(
                  color: statusColor,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatsCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;

  static const Color _cyan = Color(0xFF00F0FF);
  static const Color _gold = Color(0xFFFFB800);

  const _StatsCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black54,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _cyan.withOpacity(0.3), width: 1),
        boxShadow: [
          BoxShadow(
            color: _cyan.withOpacity(0.1),
            blurRadius: 8,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, color: _cyan, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 11,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: const TextStyle(
              color: _gold,
              fontSize: 22,
              fontWeight: FontWeight.bold,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}
