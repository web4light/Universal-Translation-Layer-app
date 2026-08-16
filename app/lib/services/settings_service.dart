import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Supported languages matching Karel IV's 9 languages.
class SupportedLanguages {
  static const List<String> codes = [
    'CS', // Čeština
    'EN', // English
    'DE', // Deutsch
    'FR', // Français
    'JA', // 日本語
    'ES', // Español
    'IT', // Italiano
    'PL', // Polski
    'SK', // Slovenčina
  ];

  static const Map<String, String> names = {
    'CS': 'Čeština',
    'EN': 'English',
    'DE': 'Deutsch',
    'FR': 'Français',
    'JA': '日本語',
    'ES': 'Español',
    'IT': 'Italiano',
    'PL': 'Polski',
    'SK': 'Slovenčina',
  };
}

/// Service for persisting app settings using SharedPreferences.
class SettingsService with ChangeNotifier {
  static const _keyN8nUrl = 'n8n_url';
  static const _keySelectedLanguage = 'selected_language';
  static const _keyMeshDaemonEnabled = 'mesh_daemon_enabled';
  static const _keyMaxCpuShare = 'max_cpu_share';
  static const _keyMaxRamShareMb = 'max_ram_share_mb';

  SharedPreferences? _prefs;

  String _n8nUrl = 'http://localhost:5678';
  String _selectedLanguage = 'CS';
  bool _isDarkMode = true; // Always true for cyberpunk theme
  bool _meshDaemonEnabled = false;
  double _maxCpuShare = 0.25;
  int _maxRamShareMb = 512;

  // ─── Public Properties ─────────────────────────────────────────────────────

  String get n8nUrl => _n8nUrl;
  String get selectedLanguage => _selectedLanguage;
  bool get isDarkMode => _isDarkMode; // Always true — cyberpunk aesthetic
  bool get meshDaemonEnabled => _meshDaemonEnabled;
  double get maxCpuShare => _maxCpuShare;
  int get maxRamShareMb => _maxRamShareMb;

  // ─── Initialization ────────────────────────────────────────────────────────

  /// Loads all settings from SharedPreferences.
  Future<void> load() async {
    _prefs = await SharedPreferences.getInstance();

    _n8nUrl = _prefs?.getString(_keyN8nUrl) ?? 'http://localhost:5678';
    _selectedLanguage = _prefs?.getString(_keySelectedLanguage) ?? 'CS';
    _meshDaemonEnabled = _prefs?.getBool(_keyMeshDaemonEnabled) ?? false;
    _maxCpuShare = _prefs?.getDouble(_keyMaxCpuShare) ?? 0.25;
    _maxRamShareMb = _prefs?.getInt(_keyMaxRamShareMb) ?? 512;

    // Validate language
    if (!SupportedLanguages.codes.contains(_selectedLanguage)) {
      _selectedLanguage = 'CS';
    }

    // Dark mode is always true for cyberpunk theme
    _isDarkMode = true;

    notifyListeners();
  }

  // ─── Setters (persist + notify) ────────────────────────────────────────────

  Future<void> setN8nUrl(String url) async {
    _n8nUrl = url;
    await _prefs?.setString(_keyN8nUrl, url);
    notifyListeners();
  }

  Future<void> setSelectedLanguage(String langCode) async {
    if (!SupportedLanguages.codes.contains(langCode)) return;
    _selectedLanguage = langCode;
    await _prefs?.setString(_keySelectedLanguage, langCode);
    notifyListeners();
  }

  Future<void> setMeshDaemonEnabled(bool enabled) async {
    _meshDaemonEnabled = enabled;
    await _prefs?.setBool(_keyMeshDaemonEnabled, enabled);
    notifyListeners();
  }

  Future<void> setMaxCpuShare(double fraction) async {
    _maxCpuShare = fraction.clamp(0.0, 1.0);
    await _prefs?.setDouble(_keyMaxCpuShare, _maxCpuShare);
    notifyListeners();
  }

  Future<void> setMaxRamShareMb(int mb) async {
    _maxRamShareMb = mb.clamp(0, 16384);
    await _prefs?.setInt(_keyMaxRamShareMb, _maxRamShareMb);
    notifyListeners();
  }

  /// Saves all current settings to SharedPreferences.
  Future<void> saveAll() async {
    await _prefs?.setString(_keyN8nUrl, _n8nUrl);
    await _prefs?.setString(_keySelectedLanguage, _selectedLanguage);
    await _prefs?.setBool(_keyMeshDaemonEnabled, _meshDaemonEnabled);
    await _prefs?.setDouble(_keyMaxCpuShare, _maxCpuShare);
    await _prefs?.setInt(_keyMaxRamShareMb, _maxRamShareMb);
  }
}
