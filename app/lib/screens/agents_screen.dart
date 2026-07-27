import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/n8n_webhook_service.dart';
import '../theme/cyberpunk_theme.dart';

enum AgentType {
  translator('Translator'),
  geallAssistant('Geall Assistant'),
  meshRouter('Mesh Router'),
  streamDubber('Stream Dubber'),
  ocrWorker('OCR Worker');

  final String label;
  const AgentType(this.label);
}

enum AgentStatus { running, stopped, error }

class Agent {
  final String id;
  final String name;
  final AgentType type;
  AgentStatus status;
  DateTime lastActivity;
  String config;

  Agent({
    required this.id,
    required this.name,
    required this.type,
    this.status = AgentStatus.stopped,
    DateTime? lastActivity,
    this.config = '',
  }) : lastActivity = lastActivity ?? DateTime.now();
}

class AgentsScreen extends StatefulWidget {
  const AgentsScreen({super.key});

  @override
  State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  final List<Agent> _agents = [
    Agent(
      id: 'agent-001',
      name: 'Primary Translator',
      type: AgentType.translator,
      status: AgentStatus.running,
      lastActivity: DateTime.now().subtract(const Duration(minutes: 2)),
    ),
    Agent(
      id: 'agent-002',
      name: 'Geall CZ Assistant',
      type: AgentType.geallAssistant,
      status: AgentStatus.running,
      lastActivity: DateTime.now().subtract(const Duration(minutes: 5)),
    ),
    Agent(
      id: 'agent-003',
      name: 'Mesh Router Alpha',
      type: AgentType.meshRouter,
      status: AgentStatus.stopped,
      lastActivity: DateTime.now().subtract(const Duration(hours: 1)),
    ),
    Agent(
      id: 'agent-004',
      name: 'Stream Dubber EN-CZ',
      type: AgentType.streamDubber,
      status: AgentStatus.error,
      lastActivity: DateTime.now().subtract(const Duration(minutes: 30)),
    ),
  ];

  bool _isDeploying = false;

  Color _statusColor(AgentStatus status) {
    switch (status) {
      case AgentStatus.running:
        return Colors.cyanAccent;
      case AgentStatus.stopped:
        return Colors.grey;
      case AgentStatus.error:
        return Colors.redAccent;
    }
  }

  String _statusLabel(AgentStatus status) {
    switch (status) {
      case AgentStatus.running:
        return 'Running';
      case AgentStatus.stopped:
        return 'Stopped';
      case AgentStatus.error:
        return 'Error';
    }
  }

  IconData _typeIcon(AgentType type) {
    switch (type) {
      case AgentType.translator:
        return Icons.translate;
      case AgentType.geallAssistant:
        return Icons.smart_toy;
      case AgentType.meshRouter:
        return Icons.router;
      case AgentType.streamDubber:
        return Icons.record_voice_over;
      case AgentType.ocrWorker:
        return Icons.document_scanner;
    }
  }

  String _timeAgo(DateTime dateTime) {
    final diff = DateTime.now().difference(dateTime);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  Future<void> _deployAgent(Agent agent) async {
    setState(() => _isDeploying = true);
    try {
      final n8nService = context.read<N8nWebhookService>();
      await n8nService.deployAgent(
        agent.name,
        agent.type.label,
        agent.config,
      );
      setState(() {
        agent.status = AgentStatus.running;
        agent.lastActivity = DateTime.now();
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Agent "${agent.name}" deployed successfully'),
            backgroundColor: Colors.green.shade700,
          ),
        );
      }
    } catch (e) {
      setState(() => agent.status = AgentStatus.error);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to deploy "${agent.name}": $e'),
            backgroundColor: Colors.red.shade700,
          ),
        );
      }
    } finally {
      setState(() => _isDeploying = false);
    }
  }

  void _showCreateAgentDialog() {
    String name = '';
    AgentType selectedType = AgentType.translator;
    String config = '';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: const Color(0xFF1E1E2E),
          title: const Text('Create New Agent', style: TextStyle(color: Colors.white)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Agent Name',
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
                    focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.cyanAccent)),
                  ),
                  style: const TextStyle(color: Colors.white),
                  onChanged: (v) => name = v,
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<AgentType>(
                  value: selectedType,
                  dropdownColor: const Color(0xFF2A2A3E),
                  decoration: const InputDecoration(
                    labelText: 'Agent Type',
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
                    focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.cyanAccent)),
                  ),
                  style: const TextStyle(color: Colors.white),
                  items: AgentType.values.map((t) => DropdownMenuItem(value: t, child: Text(t.label))).toList(),
                  onChanged: (v) { if (v != null) setDialogState(() => selectedType = v); },
                ),
                const SizedBox(height: 16),
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Configuration (JSON)',
                    labelStyle: TextStyle(color: Colors.white70),
                    enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
                    focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.cyanAccent)),
                  ),
                  style: const TextStyle(color: Colors.white),
                  maxLines: 4,
                  onChanged: (v) => config = v,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel', style: TextStyle(color: Colors.white70))),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: Colors.cyanAccent, foregroundColor: Colors.black),
              onPressed: () {
                if (name.trim().isEmpty) return;
                setState(() {
                  _agents.add(Agent(id: 'agent-${DateTime.now().millisecondsSinceEpoch}', name: name.trim(), type: selectedType, config: config));
                });
                Navigator.pop(ctx);
              },
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D1A),
      appBar: AppBar(
        title: const Text('Asgard Studio — Agents'),
        backgroundColor: const Color(0xFF1A1A2E),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: _agents.isEmpty
          ? const Center(child: Text('No agents configured.\nTap + to create one.', textAlign: TextAlign.center, style: TextStyle(color: Colors.white54, fontSize: 16)))
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _agents.length,
              itemBuilder: (context, index) => _buildAgentCard(_agents[index]),
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateAgentDialog,
        backgroundColor: Colors.cyanAccent,
        foregroundColor: Colors.black,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildAgentCard(Agent agent) {
    return Card(
      color: const Color(0xFF1E1E2E),
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(_typeIcon(agent.type), color: Colors.cyanAccent, size: 28),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(agent.name, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
                Text(agent.type.label, style: const TextStyle(color: Colors.white54, fontSize: 13)),
              ])),
              _buildStatusBadge(agent.status),
            ]),
            const SizedBox(height: 12),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text('Last activity: ${_timeAgo(agent.lastActivity)}', style: const TextStyle(color: Colors.white38, fontSize: 12)),
              Row(children: [
                if (agent.status == AgentStatus.running)
                  _buildActionButton('Stop', Icons.stop, Colors.orange, () {
                    setState(() { agent.status = AgentStatus.stopped; agent.lastActivity = DateTime.now(); });
                  }),
                const SizedBox(width: 8),
                _buildActionButton('Deploy', Icons.rocket_launch, Colors.cyanAccent, _isDeploying ? null : () => _deployAgent(agent)),
              ]),
            ]),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge(AgentStatus status) {
    final color = _statusColor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(_statusLabel(status), style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500)),
      ]),
    );
  }

  Widget _buildActionButton(String label, IconData icon, Color color, VoidCallback? onPressed) {
    return SizedBox(
      height: 32,
      child: ElevatedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 16),
        label: Text(label, style: const TextStyle(fontSize: 12)),
        style: ElevatedButton.styleFrom(
          backgroundColor: color.withOpacity(0.15),
          foregroundColor: color,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8), side: BorderSide(color: color.withOpacity(0.4))),
        ),
      ),
    );
  }
}
