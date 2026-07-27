import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Service for communicating with n8n webhooks.
/// Provides methods for GEALL queries, translation, system status, and agent deployment.
class N8nWebhookService with ChangeNotifier {
  String _baseUrl = 'http://localhost:5678';
  bool _isConnected = false;
  String? _lastError;

  String get baseUrl => _baseUrl;
  bool get isConnected => _isConnected;
  String? get lastError => _lastError;

  /// Updates the base URL for the n8n instance.
  void setBaseUrl(String url) {
    _baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    _isConnected = false;
    _lastError = null;
    notifyListeners();
  }

  /// Tests connectivity to the n8n instance.
  Future<bool> testConnection() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl/webhook/system-status'))
          .timeout(const Duration(seconds: 5));
      _isConnected = response.statusCode == 200;
      _lastError = _isConnected ? null : 'HTTP ${response.statusCode}';
    } catch (e) {
      _isConnected = false;
      _lastError = e.toString();
    }
    notifyListeners();
    return _isConnected;
  }

  /// Sends a GEALL query to the n8n webhook.
  Future<Map<String, dynamic>> geallQuery(String query) async {
    return _post('/webhook/geall-query', {'query': query});
  }

  /// Translates text between languages via the n8n webhook.
  Future<Map<String, dynamic>> translate(
    String text,
    String sourceLang,
    String targetLang,
  ) async {
    return _post('/webhook/translate', {
      'text': text,
      'source': sourceLang,
      'target': targetLang,
    });
  }

  /// Retrieves overall system status from the n8n webhook.
  Future<Map<String, dynamic>> getSystemStatus() async {
    return _get('/webhook/system-status');
  }

  /// Deploys an agent via the n8n webhook.
  Future<Map<String, dynamic>> deployAgent(
    String name,
    String type,
    Map<String, dynamic> config,
  ) async {
    return _post('/webhook/deploy-agent', {
      'name': name,
      'type': type,
      'config': config,
    });
  }

  // ─── Private Helpers ───────────────────────────────────────────────────────

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl$path'),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 30));

      _isConnected = true;
      _lastError = null;
      notifyListeners();

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        return {
          'error': true,
          'statusCode': response.statusCode,
          'message': response.body,
        };
      }
    } catch (e) {
      _isConnected = false;
      _lastError = e.toString();
      notifyListeners();
      return {
        'error': true,
        'message': e.toString(),
      };
    }
  }

  Future<Map<String, dynamic>> _get(String path) async {
    try {
      final response = await http
          .get(
            Uri.parse('$_baseUrl$path'),
            headers: {
              'Accept': 'application/json',
            },
          )
          .timeout(const Duration(seconds: 15));

      _isConnected = true;
      _lastError = null;
      notifyListeners();

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        return {
          'error': true,
          'statusCode': response.statusCode,
          'message': response.body,
        };
      }
    } catch (e) {
      _isConnected = false;
      _lastError = e.toString();
      notifyListeners();
      return {
        'error': true,
        'message': e.toString(),
      };
    }
  }
}
