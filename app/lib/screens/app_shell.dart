import 'package:flutter/material.dart';

import '../theme/cyberpunk_theme.dart';
import 'dashboard_screen.dart';
import 'translate_screen.dart';
import 'agents_screen.dart';
import 'mesh_screen.dart';
import 'settings_screen.dart';

/// The main app shell with bottom navigation and persistent tab state.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    DashboardScreen(),
    TranslateScreen(),
    AgentsScreen(),
    MeshScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(
            top: BorderSide(
              color: kCyberpunkBorderGlow,
              width: 1,
            ),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) => setState(() => _currentIndex = index),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.dashboard),
              activeIcon: _NeonIcon(icon: Icons.dashboard),
              label: 'Dashboard',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.translate),
              activeIcon: _NeonIcon(icon: Icons.translate),
              label: 'Translate',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.smart_toy),
              activeIcon: _NeonIcon(icon: Icons.smart_toy),
              label: 'Agents',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.hub),
              activeIcon: _NeonIcon(icon: Icons.hub),
              label: 'Mesh',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.settings),
              activeIcon: _NeonIcon(icon: Icons.settings),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}

/// An icon with a subtle neon glow effect for the active nav item.
class _NeonIcon extends StatelessWidget {
  const _NeonIcon({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: kCyberpunkPrimary.withOpacity(0.3),
            blurRadius: 8,
            spreadRadius: 0,
          ),
        ],
      ),
      child: Icon(
        icon,
        color: kCyberpunkPrimary,
      ),
    );
  }
}
