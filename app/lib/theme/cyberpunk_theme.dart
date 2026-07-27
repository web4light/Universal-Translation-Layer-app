import 'package:flutter/material.dart';

// ═══════════════════════════════════════════════════════════════════════════════
// Asgard Mesh Client — Cyberpunk Theme
// ═══════════════════════════════════════════════════════════════════════════════

// Core palette
const Color kCyberpunkBackground = Color(0xFF07090E);
const Color kCyberpunkSurface = Color(0xFF0D1117);
const Color kCyberpunkCard = Color(0xFF161B22);
const Color kCyberpunkPrimary = Color(0xFF00F0FF); // Cyan neon
const Color kCyberpunkSecondary = Color(0xFFFFB800); // Gold
const Color kCyberpunkError = Color(0xFFFF3366);
const Color kCyberpunkTextPrimary = Colors.white;
const Color kCyberpunkTextSecondary = Color(0xB3FFFFFF); // 70% white
const Color kCyberpunkTextTertiary = Color(0x80FFFFFF); // 50% white
const Color kCyberpunkBorderGlow = Color(0x3300F0FF); // 20% cyan

/// The main cyberpunk dark theme for Asgard Mesh Client.
final ThemeData cyberpunkTheme = ThemeData(
  brightness: Brightness.dark,
  scaffoldBackgroundColor: kCyberpunkBackground,
  primaryColor: kCyberpunkPrimary,
  colorScheme: const ColorScheme.dark(
    primary: kCyberpunkPrimary,
    secondary: kCyberpunkSecondary,
    surface: kCyberpunkSurface,
    error: kCyberpunkError,
    onPrimary: kCyberpunkBackground,
    onSecondary: kCyberpunkBackground,
    onSurface: kCyberpunkTextPrimary,
    onError: Colors.white,
  ),
  fontFamily: 'JetBrains Mono',
  textTheme: const TextTheme(
    displayLarge: TextStyle(
      color: kCyberpunkTextPrimary,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.bold,
    ),
    displayMedium: TextStyle(
      color: kCyberpunkTextPrimary,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.bold,
    ),
    headlineLarge: TextStyle(
      color: kCyberpunkTextPrimary,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.w600,
    ),
    headlineMedium: TextStyle(
      color: kCyberpunkTextPrimary,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.w600,
    ),
    titleLarge: TextStyle(
      color: kCyberpunkTextPrimary,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.w500,
    ),
    titleMedium: TextStyle(
      color: kCyberpunkTextSecondary,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.w500,
    ),
    bodyLarge: TextStyle(
      color: kCyberpunkTextPrimary,
      fontFamily: 'JetBrains Mono',
    ),
    bodyMedium: TextStyle(
      color: kCyberpunkTextSecondary,
      fontFamily: 'JetBrains Mono',
    ),
    bodySmall: TextStyle(
      color: kCyberpunkTextTertiary,
      fontFamily: 'JetBrains Mono',
    ),
    labelLarge: TextStyle(
      color: kCyberpunkBackground,
      fontFamily: 'JetBrains Mono',
      fontWeight: FontWeight.w600,
    ),
  ),
  cardColor: kCyberpunkCard,
  cardTheme: CardTheme(
    color: kCyberpunkCard,
    elevation: 0,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(12),
      side: const BorderSide(color: kCyberpunkBorderGlow, width: 1),
    ),
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: Colors.transparent,
    elevation: 0,
    centerTitle: true,
    titleTextStyle: TextStyle(
      color: kCyberpunkPrimary,
      fontFamily: 'JetBrains Mono',
      fontSize: 18,
      fontWeight: FontWeight.w600,
    ),
    iconTheme: IconThemeData(color: kCyberpunkPrimary),
  ),
  bottomNavigationBarTheme: const BottomNavigationBarThemeData(
    backgroundColor: kCyberpunkSurface,
    selectedItemColor: kCyberpunkPrimary,
    unselectedItemColor: kCyberpunkTextTertiary,
    type: BottomNavigationBarType.fixed,
    elevation: 0,
    selectedLabelStyle: TextStyle(
      fontFamily: 'JetBrains Mono',
      fontSize: 10,
      fontWeight: FontWeight.w600,
    ),
    unselectedLabelStyle: TextStyle(
      fontFamily: 'JetBrains Mono',
      fontSize: 10,
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: kCyberpunkSurface,
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: kCyberpunkBorderGlow),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: kCyberpunkBorderGlow),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: kCyberpunkPrimary, width: 1.5),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: const BorderSide(color: kCyberpunkError),
    ),
    labelStyle: const TextStyle(
      color: kCyberpunkTextTertiary,
      fontFamily: 'JetBrains Mono',
    ),
    hintStyle: const TextStyle(
      color: kCyberpunkTextTertiary,
      fontFamily: 'JetBrains Mono',
    ),
  ),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style: ElevatedButton.styleFrom(
      backgroundColor: kCyberpunkPrimary,
      foregroundColor: kCyberpunkBackground,
      elevation: 0,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      textStyle: const TextStyle(
        fontFamily: 'JetBrains Mono',
        fontWeight: FontWeight.w600,
        fontSize: 14,
      ),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      foregroundColor: kCyberpunkPrimary,
      side: const BorderSide(color: kCyberpunkPrimary),
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      textStyle: const TextStyle(
        fontFamily: 'JetBrains Mono',
        fontWeight: FontWeight.w600,
        fontSize: 14,
      ),
    ),
  ),
  iconTheme: const IconThemeData(color: kCyberpunkPrimary),
  dividerColor: kCyberpunkBorderGlow,
  dividerTheme: const DividerThemeData(
    color: kCyberpunkBorderGlow,
    thickness: 1,
  ),
);

// ═══════════════════════════════════════════════════════════════════════════════
// Helper Widgets
// ═══════════════════════════════════════════════════════════════════════════════

/// A card with a subtle cyan neon border glow effect.
class CyberpunkCard extends StatelessWidget {
  const CyberpunkCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.glowIntensity = 0.2,
  });

  final Widget child;
  final EdgeInsets padding;
  final double glowIntensity;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: kCyberpunkCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: kCyberpunkPrimary.withOpacity(glowIntensity),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: kCyberpunkPrimary.withOpacity(glowIntensity * 0.3),
            blurRadius: 8,
            spreadRadius: 0,
          ),
        ],
      ),
      padding: padding,
      child: child,
    );
  }
}

/// A neon-styled section header with a cyan accent line.
class CyberpunkSectionHeader extends StatelessWidget {
  const CyberpunkSectionHeader({
    super.key,
    required this.title,
    this.trailing,
  });

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Container(
            width: 3,
            height: 20,
            decoration: BoxDecoration(
              color: kCyberpunkPrimary,
              borderRadius: BorderRadius.circular(2),
              boxShadow: [
                BoxShadow(
                  color: kCyberpunkPrimary.withOpacity(0.5),
                  blurRadius: 4,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              title.toUpperCase(),
              style: const TextStyle(
                color: kCyberpunkTextPrimary,
                fontFamily: 'JetBrains Mono',
                fontSize: 13,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2,
              ),
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

/// A glowing divider with cyan neon effect.
class CyberpunkDivider extends StatelessWidget {
  const CyberpunkDivider({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 1,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            kCyberpunkPrimary.withOpacity(0),
            kCyberpunkPrimary.withOpacity(0.3),
            kCyberpunkPrimary.withOpacity(0),
          ],
        ),
      ),
    );
  }
}

/// An AppBar with the cyberpunk bottom cyan border.
PreferredSizeWidget cyberpunkAppBar({
  required String title,
  List<Widget>? actions,
  Widget? leading,
}) {
  return AppBar(
    title: Text(title),
    leading: leading,
    actions: actions,
    bottom: PreferredSize(
      preferredSize: const Size.fromHeight(1),
      child: Container(
        height: 1,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              kCyberpunkPrimary.withOpacity(0),
              kCyberpunkPrimary.withOpacity(0.6),
              kCyberpunkPrimary.withOpacity(0),
            ],
          ),
        ),
      ),
    ),
  );
}

/// Static accessor for the cyberpunk theme.
class CyberpunkTheme {
  CyberpunkTheme._();
  static ThemeData get darkTheme => cyberpunkTheme;
}
