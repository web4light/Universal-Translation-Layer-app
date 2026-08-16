import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/n8n_webhook_service.dart';
import '../theme/cyberpunk_theme.dart';

/// Karel IV. Real-Time Translation interface.
class TranslateScreen extends StatefulWidget {
  const TranslateScreen({super.key});

  @override
  State<TranslateScreen> createState() => _TranslateScreenState();
}

class _TranslateScreenState extends State<TranslateScreen> {
  static const Color _cyan = Color(0xFF00F0FF);
  static const Color _gold = Color(0xFFFFB800);

  static const Map<String, String> _languages = {
    'CS': 'Czech',
    'EN': 'English',
    'DE': 'German',
    'FR': 'French',
    'JA': 'Japanese',
    'ES': 'Spanish',
    'IT': 'Italian',
    'PL': 'Polish',
    'SK': 'Slovak',
  };

  final TextEditingController _sourceController = TextEditingController();
  String _sourceLanguage = 'CS';
  String _targetLanguage = 'EN';
  String? _translatedText;
  bool _isTranslating = false;

  /// Translation history — last 10 entries (newest first).
  final List<_TranslationEntry> _history = [];

  @override
  void dispose() {
    _sourceController.dispose();
    super.dispose();
  }

  void _swapLanguages() {
    setState(() {
      final temp = _sourceLanguage;
      _sourceLanguage = _targetLanguage;
      _targetLanguage = temp;
    });
  }

  Future<void> _translate() async {
    final text = _sourceController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _isTranslating = true;
      _translatedText = null;
    });

    try {
      final n8nService = context.read<N8nWebhookService>();
      final result = await n8nService.translate(
        text,
        _sourceLanguage,
        _targetLanguage,
      );

      setState(() {
        if (result.containsKey('error') && result['error'] == true) {
          _translatedText = 'Error: ${result['message'] ?? 'Unknown error'}';
        } else {
          _translatedText = result['translated'] as String? ?? result.toString();
        }
        _isTranslating = false;

        // Add to history (max 10 entries)
        _history.insert(
          0,
          _TranslationEntry(
            sourceText: text,
            translatedText: _translatedText ?? "",
            sourceLanguage: _sourceLanguage,
            targetLanguage: _targetLanguage,
            timestamp: DateTime.now(),
          ),
        );
        if (_history.length > 10) {
          _history.removeLast();
        }
      });
    } catch (e) {
      setState(() {
        _isTranslating = false;
        _translatedText = 'Error: ${e.toString()}';
      });
    }
  }

  void _copyResult() {
    if (_translatedText != null && _translatedText!.isNotEmpty) {
      Clipboard.setData(ClipboardData(text: _translatedText!));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Copied to clipboard'),
          duration: Duration(seconds: 1),
          backgroundColor: Color(0xFF1A1A2E),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('KAREL IV. — TRANSLATION'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            const Text(
              'Real-Time Translation',
              style: TextStyle(
                color: _cyan,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                letterSpacing: 2.0,
                fontFamily: 'monospace',
              ),
            ),
            const SizedBox(height: 16),

            // Language selection row
            _buildLanguageSelector(),
            const SizedBox(height: 16),

            // Source text input
            _buildSourceInput(),
            const SizedBox(height: 16),

            // Translate button
            _buildTranslateButton(),
            const SizedBox(height: 16),

            // Result area
            _buildResultArea(),
            const SizedBox(height: 24),

            // Translation history
            if (_history.isNotEmpty) ...[
              const Text(
                'HISTORY',
                style: TextStyle(
                  color: _cyan,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 2.0,
                  fontFamily: 'monospace',
                ),
              ),
              const SizedBox(height: 12),
              _buildHistory(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildLanguageSelector() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
      child: Row(
        children: [
          // Source language dropdown
          Expanded(child: _buildDropdown(_sourceLanguage, (val) {
            setState(() => _sourceLanguage = val!);
          })),

          // Swap button
          IconButton(
            icon: const Icon(Icons.swap_horiz, color: _gold),
            onPressed: _swapLanguages,
            tooltip: 'Swap languages',
          ),

          // Target language dropdown
          Expanded(child: _buildDropdown(_targetLanguage, (val) {
            setState(() => _targetLanguage = val!);
          })),
        ],
      ),
    );
  }

  Widget _buildDropdown(String value, ValueChanged<String?> onChanged) {
    return DropdownButtonFormField<String>(
      value: value,
      onChanged: onChanged,
      dropdownColor: const Color(0xFF1A1A2E),
      style: const TextStyle(
        color: Colors.white,
        fontSize: 14,
        fontFamily: 'monospace',
      ),
      decoration: const InputDecoration(
        border: InputBorder.none,
        contentPadding: EdgeInsets.symmetric(horizontal: 8),
        isDense: true,
      ),
      items: _languages.entries.map((entry) {
        return DropdownMenuItem<String>(
          value: entry.key,
          child: Text(
            '${entry.key} — ${entry.value}',
            style: const TextStyle(fontSize: 13),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildSourceInput() {
    return Container(
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
      child: TextField(
        controller: _sourceController,
        maxLines: 6,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontFamily: 'monospace',
        ),
        decoration: InputDecoration(
          hintText: 'Enter text to translate...',
          hintStyle: TextStyle(
            color: Colors.white.withOpacity(0.3),
            fontFamily: 'monospace',
          ),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.all(16),
        ),
      ),
    );
  }

  Widget _buildTranslateButton() {
    return SizedBox(
      height: 48,
      child: ElevatedButton(
        onPressed: _isTranslating ? null : _translate,
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.transparent,
          foregroundColor: _cyan,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
            side: const BorderSide(color: _cyan, width: 1.5),
          ),
          elevation: 0,
        ).copyWith(
          overlayColor: WidgetStateProperty.all(_cyan.withOpacity(0.1)),
        ),
        child: _isTranslating
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: _cyan,
                ),
              )
            : const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.translate, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'TRANSLATE',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _buildResultArea() {
    if (_translatedText == null && !_isTranslating) {
      return const SizedBox.shrink();
    }

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
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'RESULT',
                style: TextStyle(
                  color: _cyan,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                  fontFamily: 'monospace',
                ),
              ),
              if (_translatedText != null)
                IconButton(
                  icon: const Icon(Icons.copy, size: 18, color: _cyan),
                  onPressed: _copyResult,
                  tooltip: 'Copy to clipboard',
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
            ],
          ),
          const SizedBox(height: 10),
          if (_isTranslating)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(20),
                child: CircularProgressIndicator(color: _cyan, strokeWidth: 2),
              ),
            )
          else
            SelectableText(
              _translatedText ?? '',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontFamily: 'monospace',
                height: 1.5,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildHistory() {
    return Column(
      children: _history.map((entry) {
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.black38,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: Colors.white10),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    '${entry.sourceLanguage} → ${entry.targetLanguage}',
                    style: const TextStyle(
                      color: _gold,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const Spacer(),
                  Text(
                    _formatTime(entry.timestamp),
                    style: const TextStyle(
                      color: Colors.white24,
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                entry.sourceText,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white54,
                  fontSize: 12,
                  fontFamily: 'monospace',
                ),
              ),
              const SizedBox(height: 4),
              Text(
                entry.translatedText,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:'
        '${time.minute.toString().padLeft(2, '0')}';
  }
}

/// Internal model for storing translation history entries.
class _TranslationEntry {
  final String sourceText;
  final String translatedText;
  final String sourceLanguage;
  final String targetLanguage;
  final DateTime timestamp;

  const _TranslationEntry({
    required this.sourceText,
    required this.translatedText,
    required this.sourceLanguage,
    required this.targetLanguage,
    required this.timestamp,
  });
}
