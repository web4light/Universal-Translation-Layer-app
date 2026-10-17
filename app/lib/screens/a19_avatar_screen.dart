import 'dart:async';
import 'package:flutter/material.dart';

import '../services/a19_rust_ai_service.dart';
import '../theme/cyberpunk_theme.dart';
import '../widgets/glowing_card.dart';

/// Obrazovka A19 Pro On-Device AI & 120Hz 3D Znakového Avatara v Rustu.
class A19AvatarScreen extends StatefulWidget {
  const A19AvatarScreen({super.key});

  @override
  State<A19AvatarScreen> createState() => _A19AvatarScreenState();
}

class _A19AvatarScreenState extends State<A19AvatarScreen>
    with SingleTickerProviderStateMixin {
  final A19RustAiService _aiService = A19RustAiService();
  final TextEditingController _inputController = TextEditingController(
    text: 'Vítejte v Asgardu, suverénní překlad a přístupnost v RAM',
  );

  late final AnimationController _animController;
  int _activeGlossId = 1;
  String _selectedLang = 'SIGN';
  String _translatedOutput =
      '[3D ZNAKOVÁ ŘEČ A19 PRO]: VÍTEJTE (WELCOME) → SUVERENITA (SOVEREIGN)';
  int _latencyUs = 3;
  double _elapsedSec = 0.0;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3600),
    )..addListener(() {
        setState(() {
          _elapsedSec += 1.0 / 60.0;
        });
      });
    _animController.repeat();
    _runInference();
  }

  @override
  void dispose() {
    _animController.dispose();
    _inputController.dispose();
    super.dispose();
  }

  void _runInference() {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;
    final res = _aiService.inferOnDevice(text, _selectedLang);
    setState(() {
      _activeGlossId = res['primary_gloss_id'] as int;
      _translatedOutput = res['translated'] as String;
      _latencyUs = res['latency_us'] as int;
    });
  }

  void _triggerAshSweep() {
    final count = _aiService.ashSweep423();
    setState(() {
      _activeGlossId = 0;
      _translatedOutput =
          '[04:23 ASH SWEEPER #$count]: 64KB UMA RAM aréna kompletně vynulována.';
    });
  }

  @override
  Widget build(BuildContext context) {
    final frame = _aiService.solveAvatarFrame(_elapsedSec, _activeGlossId);
    final glossLabel =
        A19RustAiService.glossNames[_activeGlossId] ?? 'KLID (IDLE)';

    return Scaffold(
      appBar: AppBar(
        title: const Text('A19 PRO // RUST AI & AVATAR'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: kCyberpunkPrimary.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: kCyberpunkPrimary, width: 1),
                ),
                child: Text(
                  '$_latencyUs µs | UMA Q8_0',
                  style: const TextStyle(
                    color: kCyberpunkPrimary,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 3D Holografický Znakový Avatar (120Hz ProMotion solver)
            GlowingCard(
              glowColor: kCyberpunkPrimary,
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.bolt,
                              color: kCyberpunkPrimary, size: 18),
                          const SizedBox(width: 6),
                          Text(
                            glossLabel,
                            style: const TextStyle(
                              color: kCyberpunkPrimary,
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        'RAM: ${_aiService.ramUsedBytes} B | Sweeps: ${_aiService.sweepsCount}',
                        style: const TextStyle(
                          color: kCyberpunkTextSecondary,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 250,
                    width: double.infinity,
                    child: CustomPaint(
                      painter: _A19AvatarPainter(frame: frame),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    alignment: WrapAlignment.center,
                    children: A19RustAiService.glossNames.entries.map((e) {
                      final selected = e.key == _activeGlossId;
                      return ChoiceChip(
                        label: Text(
                          e.value.split(' ').first,
                          style: TextStyle(
                            fontSize: 11,
                            color:
                                selected ? Colors.black : kCyberpunkTextPrimary,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        selected: selected,
                        selectedColor: kCyberpunkPrimary,
                        backgroundColor: kCyberpunkSurface,
                        onSelected: (_) =>
                            setState(() => _activeGlossId = e.key),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Vstupní pole pro okamžitou On-Device Rust inferenci
            GlowingCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'ON-DEVICE NEURAL ENGINE (RUST ZERO-COPY)',
                    style: TextStyle(
                      color: kCyberpunkSecondary,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                      letterSpacing: 1.1,
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _inputController,
                    maxLines: 2,
                    style: const TextStyle(color: kCyberpunkTextPrimary),
                    decoration: const InputDecoration(
                      hintText: 'Zadej větu pro okamžitý on-device překlad...',
                    ),
                    onChanged: (_) => _runInference(),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      for (final lang in ['SIGN', 'CS', 'EN', 'LA'])
                        Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: ChoiceChip(
                            label: Text(lang),
                            selected: _selectedLang == lang,
                            selectedColor: kCyberpunkSecondary,
                            onSelected: (_) {
                              setState(() => _selectedLang = lang);
                              _runInference();
                            },
                          ),
                        ),
                      const Spacer(),
                      ElevatedButton.icon(
                        onPressed: _triggerAshSweep,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.redAccent.withOpacity(0.2),
                          foregroundColor: Colors.redAccent,
                          side: const BorderSide(color: Colors.redAccent),
                        ),
                        icon: const Icon(Icons.cleaning_services, size: 16),
                        label: const Text('04:23 SWEEP'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.black45,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: kCyberpunkPrimary.withOpacity(0.4),
                      ),
                    ),
                    child: Text(
                      _translatedOutput,
                      style: const TextStyle(
                        color: kCyberpunkPrimary,
                        fontFamily: 'monospace',
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _A19AvatarPainter extends CustomPainter {
  final A19AvatarFrame frame;

  _A19AvatarPainter({required this.frame});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2 + 12;

    // Holografická mřížka na pozadí
    final gridPaint = Paint()
      ..color = kCyberpunkPrimary.withOpacity(0.08)
      ..strokeWidth = 1;
    for (double x = 0; x < size.width; x += 28) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y < size.height; y += 28) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    // Energetická aura A19 Pro
    if (frame.energyPulse > 0.05) {
      final auraPaint = Paint()
        ..color = kCyberpunkPrimary.withOpacity(0.12 * frame.energyPulse)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 24);
      canvas.drawCircle(
        Offset(cx, cy - 10),
        75 * frame.energyPulse,
        auraPaint,
      );
    }

    // Trup a krk
    final bodyPaint = Paint()
      ..color = kCyberpunkSecondary.withOpacity(0.75)
      ..strokeWidth = 3.0
      ..style = PaintingStyle.stroke;

    final lSh = Offset(cx + frame.leftArm.shoulder.x, cy + frame.leftArm.shoulder.y);
    final rSh = Offset(cx + frame.rightArm.shoulder.x, cy + frame.rightArm.shoulder.y);
    final pelvis = Offset(cx, cy + 68 + frame.breathOffsetY);

    final torsoPath = Path()
      ..moveTo(lSh.dx, lSh.dy)
      ..lineTo(rSh.dx, rSh.dy)
      ..lineTo(pelvis.dx + 20, pelvis.dy)
      ..lineTo(pelvis.dx - 20, pelvis.dy)
      ..close();
    canvas.drawPath(torsoPath, bodyPaint);

    // Hlava
    final headCenter = Offset(
      cx + frame.headTiltRad * 25,
      cy - 54 + frame.breathOffsetY,
    );
    final headPaint = Paint()
      ..color = kCyberpunkPrimary
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke;
    canvas.drawCircle(headCenter, 22, headPaint);

    // Oči a artikulace rtů
    final eyePaint = Paint()..color = kCyberpunkPrimary;
    canvas.drawCircle(headCenter.translate(-7, -4), 2.5, eyePaint);
    canvas.drawCircle(headCenter.translate(7, -4), 2.5, eyePaint);
    canvas.drawOval(
      Rect.fromCenter(
        center: headCenter.translate(0, 8),
        width: 11,
        height: 2.0 + frame.mouthOpen * 7.0,
      ),
      headPaint,
    );

    // Vykreslení obou paží a 10 prstů
    _drawArm(canvas, cx, cy, frame.leftArm);
    _drawArm(canvas, cx, cy, frame.rightArm);
  }

  void _drawArm(Canvas canvas, double cx, double cy, A19ArmPose arm) {
    final sh = Offset(cx + arm.shoulder.x, cy + arm.shoulder.y);
    final el = Offset(cx + arm.elbow.x, cy + arm.elbow.y);
    final wr = Offset(cx + arm.wrist.x, cy + arm.wrist.y);

    final bonePaint = Paint()
      ..color = kCyberpunkPrimary
      ..strokeWidth = 4.0
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(sh, el, bonePaint);
    canvas.drawLine(el, wr, bonePaint);

    final jointPaint = Paint()..color = Colors.white;
    canvas.drawCircle(sh, 4, jointPaint);
    canvas.drawCircle(el, 4, jointPaint);
    canvas.drawCircle(wr, 4.5, jointPaint);

    final fingerPaint = Paint()
      ..color = kCyberpunkSecondary
      ..strokeWidth = 2.0
      ..strokeCap = StrokeCap.round;

    for (final f in arm.fingers) {
      final mid = Offset(cx + f.mid.x, cy + f.mid.y);
      final tip = Offset(cx + f.tip.x, cy + f.tip.y);
      canvas.drawLine(wr, mid, fingerPaint);
      canvas.drawLine(mid, tip, fingerPaint);
      canvas.drawCircle(tip, 2.0, Paint()..color = kCyberpunkPrimary);
    }
  }

  @override
  bool shouldRepaint(covariant _A19AvatarPainter oldDelegate) => true;
}
