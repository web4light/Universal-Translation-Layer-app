import 'package:flutter/material.dart';
import '../theme/cyberpunk_theme.dart';

/// Neonově podsvícená karta pro cyberpunkové rozhraní Asgard Mesh.
class GlowingCard extends StatelessWidget {
  final Widget child;
  final Color glowColor;
  final EdgeInsetsGeometry padding;
  final double borderRadius;

  const GlowingCard({
    super.key,
    required this.child,
    this.glowColor = kCyberpunkPrimary,
    this.padding = const EdgeInsets.all(16),
    this.borderRadius = 16,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: kCyberpunkCard,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(
          color: glowColor.withAlpha(115),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: glowColor.withAlpha(41),
            blurRadius: 18,
            spreadRadius: 1,
          ),
        ],
      ),
      child: child,
    );
  }
}
