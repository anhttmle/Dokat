import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'features/auth/domain/auth_state.dart';
import 'features/auth/presentation/providers/auth_notifier.dart';
import 'features/auth/presentation/screens/force_link_screen.dart';
import 'features/auth/presentation/widgets/auth_guard.dart';
import 'features/capture/presentation/screens/camera_screen.dart';
import 'features/feed/presentation/screens/feed_screen.dart';
import 'features/history/presentation/screens/history_screen.dart';
import 'features/profile/presentation/screens/pet_timeline_screen.dart';
import 'features/profile/presentation/screens/profile_screen.dart';
import 'features/send/presentation/screens/recipient_selector_screen.dart';
import 'features/settings/presentation/screens/settings_screen.dart';
import 'features/social/presentation/screens/add_friend_screen.dart';
import 'features/social/presentation/screens/friend_list_screen.dart';
import 'features/social/presentation/screens/qr_scanner_screen.dart';

/// Provides the [GoRouter] instance, rebuilds when auth state changes.
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authNotifierProvider);

  return GoRouter(
    initialLocation: '/feed',
    redirect: (context, state) {
      if (authState is AuthLoading) return null;
      if (authState is AuthUnauthenticated) return null;
      if (authState is AuthForceLinkRequired) {
        if (state.matchedLocation != '/force-link') return '/force-link';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/force-link',
        builder: (_, __) => const ForceLinkScreen(),
      ),
      GoRoute(
        path: '/camera',
        builder: (_, __) => const AuthGuard(child: CameraScreen()),
      ),
      GoRoute(
        path: '/send/recipients',
        builder: (_, state) {
          final imageData = state.extra as Map<String, dynamic>? ?? {};
          return AuthGuard(
            child: RecipientSelectorScreen(imageData: imageData),
          );
        },
      ),
      StatefulShellRoute.indexedStack(
        builder: (_, __, navigationShell) =>
            _AppShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/feed',
                builder: (_, __) => const AuthGuard(child: FeedScreen()),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/friends',
                builder: (_, __) =>
                    const AuthGuard(child: FriendListScreen()),
                routes: [
                  GoRoute(
                    path: 'add',
                    builder: (_, __) =>
                        const AuthGuard(child: AddFriendScreen()),
                  ),
                  GoRoute(
                    path: 'scan',
                    builder: (_, __) =>
                        const AuthGuard(child: QRScannerScreen()),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/history',
                builder: (_, __) => const AuthGuard(child: HistoryScreen()),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/settings',
                builder: (_, __) => const SettingsScreen(),
                routes: [
                  GoRoute(
                    path: 'profile',
                    builder: (_, __) => const ProfileScreen(),
                    routes: [
                      GoRoute(
                        path: 'pet/:petId',
                        builder: (_, state) => PetTimelineScreen(
                          petId: state.pathParameters['petId']!,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

/// Bottom navigation shell widget.
class _AppShell extends StatelessWidget {
  const _AppShell({required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: navigationShell.goBranch,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Feed',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline),
            selectedIcon: Icon(Icons.people),
            label: 'Friends',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history),
            label: 'History',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

/// Root app widget.
class DokatApp extends ConsumerWidget {
  const DokatApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Dokat',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF6750A4)),
        useMaterial3: true,
      ),
      routerConfig: router,
    );
  }
}
