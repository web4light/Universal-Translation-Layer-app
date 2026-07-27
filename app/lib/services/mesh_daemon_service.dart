import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'n8n_webhook_service.dart';

/// Represents a single peer in the Asgard Mesh network.
class MeshPeer {
  final String id;
  final String ip;
  final String status;
  final double cpuUsage;
  final int ramMb;
  final int tasksCompleted;

  MeshPeer({
    required this.id,
    required this.ip,
    required this.status,
    required this.cpuUsage,
    required this.ramMb,
    required this.tasksCompleted,
  });

  factory MeshPeer.fromJson(Map<String, dynamic> json) {
    return MeshPeer(
      id: json['id'] as String? ?? '',
      ip: json['ip'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
      cpuUsage: (json['cpuUsage'] as num?)?.toDouble() ?? 0.0,
      ramMb: json['ramMb'] as int? ?? 0,
      tasksCompleted: json['tasksCompleted'] as int? ?? 0,
    );
  }
}

/// Service managing the local mesh daemon.
/// Simulates mesh activity for demo and integrates with N8nWebhookService for real calls.
class MeshDaemonService with ChangeNotifier {
  final N8nWebhookService _webhookService;

  bool _isRunning = false;
  double _cpuContribution = 0.25;
  int _ramContributionMb = 512;
  int _connectedPeers = 0;
  int _totalTasksProcessed = 0;
  Duration _uptime = Duration.zero;
  List<MeshPeer> _peersInfo = [];

  Timer? _statusTimer;
  Timer? _uptimeTimer;
  DateTime? _startedAt;

  final _random = Random();

  MeshDaemonService(this._webhookService);

  // ─── Public Properties ─────────────────────────────────────────────────────

  bool get isRunning => _isRunning;
  double get cpuContribution => _cpuContribution;
  int get ramContributionMb => _ramContributionMb;
  int get connectedPeers => _connectedPeers;
  int get totalTasksProcessed => _totalTasksProcessed;
  Duration get uptime => _uptime;
  List<MeshPeer> get peersInfo => List.unmodifiable(_peersInfo);

  // ─── Public Methods ────────────────────────────────────────────────────────

  /// Starts the mesh daemon, begins periodic status polling.
  Future<void> start() async {
    if (_isRunning) return;

    _isRunning = true;
    _startedAt = DateTime.now();
    _totalTasksProcessed = 0;
    _connectedPeers = 0;
    _peersInfo = [];
    notifyListeners();

    // Poll status every 5 seconds
    _statusTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => refreshStatus(),
    );

    // Update uptime every second
    _uptimeTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => _updateUptime(),
    );

    // Initial status fetch
    await refreshStatus();
  }

  /// Stops the mesh daemon.
  Future<void> stop() async {
    _isRunning = false;
    _statusTimer?.cancel();
    _statusTimer = null;
    _uptimeTimer?.cancel();
    _uptimeTimer = null;
    _startedAt = null;
    _uptime = Duration.zero;
    _connectedPeers = 0;
    _peersInfo = [];
    notifyListeners();
  }

  /// Sets the maximum CPU fraction (0.0–1.0) to contribute to the mesh.
  void setCpuLimit(double fraction) {
    _cpuContribution = fraction.clamp(0.0, 1.0);
    notifyListeners();
  }

  /// Sets the maximum RAM in MB to contribute to the mesh.
  void setRamLimit(int mb) {
    _ramContributionMb = mb.clamp(0, 16384);
    notifyListeners();
  }

  /// Polls the n8n webhook for mesh status; falls back to simulated data.
  Future<void> refreshStatus() async {
    if (!_isRunning) return;

    try {
      final result = await _webhookService.getSystemStatus();

      if (result.containsKey('error') && result['error'] == true) {
        // Backend unavailable — simulate mesh activity for demo
        _simulateActivity();
      } else {
        _connectedPeers = result['connectedPeers'] as int? ?? _connectedPeers;
        _totalTasksProcessed =
            result['totalTasksProcessed'] as int? ?? _totalTasksProcessed;

        final peersJson = result['peers'] as List<dynamic>?;
        if (peersJson != null) {
          _peersInfo = peersJson
              .map((p) => MeshPeer.fromJson(p as Map<String, dynamic>))
              .toList();
        }
      }
    } catch (_) {
      _simulateActivity();
    }

    notifyListeners();
  }

  @override
  void dispose() {
    _statusTimer?.cancel();
    _uptimeTimer?.cancel();
    super.dispose();
  }

  // ─── Private Helpers ───────────────────────────────────────────────────────

  void _updateUptime() {
    if (_startedAt != null) {
      _uptime = DateTime.now().difference(_startedAt!);
      notifyListeners();
    }
  }

  /// Simulates mesh activity for demo/offline mode.
  void _simulateActivity() {
    // Randomly fluctuate connected peers (1–7)
    _connectedPeers = 1 + _random.nextInt(7);

    // Increment processed tasks
    _totalTasksProcessed += _random.nextInt(3);

    // Generate simulated peer info
    _peersInfo = List.generate(_connectedPeers, (i) {
      return MeshPeer(
        id: 'peer-${i.toString().padLeft(3, '0')}',
        ip: '192.168.1.${10 + i}',
        status: _random.nextDouble() > 0.15 ? 'active' : 'idle',
        cpuUsage: (_random.nextDouble() * 0.8).clamp(0.0, 1.0),
        ramMb: 128 + _random.nextInt(896),
        tasksCompleted: _random.nextInt(50),
      );
    });
  }
}
