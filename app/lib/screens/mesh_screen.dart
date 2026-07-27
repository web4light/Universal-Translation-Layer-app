import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/mesh_daemon_service.dart';
import '../theme/cyberpunk_theme.dart';

class MeshScreen extends StatefulWidget {
  const MeshScreen({super.key});

  @override
  State<MeshScreen> createState() => _MeshScreenState();
}

class _MeshScreenState extends State<MeshScreen> with WidgetsBindingObserver {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _startAutoRefresh();
    } else {
      _refreshTimer?.cancel();
    }
  }

  void _startAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted) {
        context.read<MeshDaemonService>().refreshStatus();
      }
    });
  }

  Color _peerStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'online':
        return Colors.cyanAccent;
      case 'degraded':
        return const Color(0xFFFFD700);
      case 'offline':
        return Colors.redAccent;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final meshService = context.watch<MeshDaemonService>();

    return Scaffold(
      backgroundColor: const Color(0xFF0D0D1A),
      appBar: AppBar(
        title: const Text('Mesh Network'),
        backgroundColor: const Color(0xFF1A1A2E),
        foregroundColor: Colors.white,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => meshService.refreshStatus(),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeaderStats(meshService),
            const SizedBox(height: 24),
            _buildSectionTitle('Network Peers'),
            const SizedBox(height: 12),
            _buildPeerList(meshService),
            const SizedBox(height: 24),
            _buildSectionTitle('Your Contribution'),
            const SizedBox(height: 12),
            _buildContributionStats(meshService),
          ],
        ),
      ),
    );
  }

  Widget _buildHeaderStats(MeshDaemonService meshService) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E2E),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem('Total Nodes', '${meshService.connectedPeers}', Icons.device_hub),
          _buildStatItem('Active', '${meshService.connectedPeers}', Icons.check_circle_outline),
          _buildStatItem('Uptime', _formatDuration(meshService.uptime), Icons.timer),
          _buildStatItem('Tasks', '${meshService.totalTasksProcessed}', Icons.task_alt),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, color: Colors.cyanAccent, size: 24),
        const SizedBox(height: 6),
        Text(value, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 11)),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(title, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600));
  }

  Widget _buildPeerList(MeshDaemonService meshService) {
    final peers = meshService.peersInfo;
    if (peers.isEmpty) {
      return const Center(child: Padding(
        padding: EdgeInsets.all(32),
        child: Text('No peers discovered yet.', style: TextStyle(color: Colors.white54)),
      ));
    }
    return Column(
      children: peers.map((peer) => _buildPeerCard(peer)).toList(),
    );
  }

  Widget _buildPeerCard(MeshPeer peer) {
    final statusColor = _peerStatusColor(peer.status);
    return Card(
      color: const Color(0xFF1E1E2E),
      margin: const EdgeInsets.only(bottom: 10),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                width: 10, height: 10,
                decoration: BoxDecoration(color: statusColor, shape: BoxShape.circle),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  peer.id.length > 12 ? '${peer.id.substring(0, 12)}...' : peer.id,
                  style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500, fontFamily: 'monospace'),
                ),
              ),
              Text(peer.status.toUpperCase(), style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.w600)),
            ]),
            const SizedBox(height: 10),
            Row(children: [
              const Icon(Icons.lan, size: 14, color: Colors.white38),
              const SizedBox(width: 6),
              Text(peer.ip, style: const TextStyle(color: Colors.white54, fontSize: 12)),
              const Spacer(),
              const Icon(Icons.task, size: 14, color: Colors.white38),
              const SizedBox(width: 6),
              Text('${peer.tasksCompleted} tasks', style: const TextStyle(color: Colors.white54, fontSize: 12)),
            ]),
            const SizedBox(height: 10),
            Row(children: [
              const Text('CPU ', style: TextStyle(color: Colors.white38, fontSize: 11)),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: peer.cpuUsage / 100,
                    backgroundColor: Colors.white12,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      peer.cpuUsage > 80 ? Colors.redAccent : Colors.cyanAccent,
                    ),
                    minHeight: 6,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text('${peer.cpuUsage.toInt()}%', style: const TextStyle(color: Colors.white54, fontSize: 11)),
              const SizedBox(width: 16),
              Text('RAM ${peer.ramMb} MB', style: const TextStyle(color: Colors.white54, fontSize: 11)),
            ]),
          ],
        ),
      ),
    );
  }

  Widget _buildContributionStats(MeshDaemonService meshService) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E2E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          _buildContributionRow(Icons.memory, 'Your CPU shared', '${(meshService.cpuContribution * 100).toStringAsFixed(0)}%'),
          const Divider(color: Colors.white12, height: 20),
          _buildContributionRow(Icons.storage, 'Your RAM shared', '${meshService.ramContributionMb} MB'),
          const Divider(color: Colors.white12, height: 20),
          _buildContributionRow(Icons.done_all, 'Tasks you processed', '${meshService.totalTasksProcessed}'),
        ],
      ),
    );
  }

  Widget _buildContributionRow(IconData icon, String label, String value) {
    return Row(children: [
      Icon(icon, color: Colors.cyanAccent, size: 20),
      const SizedBox(width: 12),
      Expanded(child: Text(label, style: const TextStyle(color: Colors.white70, fontSize: 14))),
      Text(value, style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
    ]);
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
