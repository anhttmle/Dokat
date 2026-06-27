/**
 * Dokat — Root Application Component
 *
 * Bootstraps Firebase Auth, then routes to:
 *   - ForceLinkScreen  (when backend requires OAuth linking)
 *   - MainTabs         (authenticated main app)
 *
 * Navigation structure:
 *   Root Stack
 *     ├── MainTabs (Bottom Tab Navigator)
 *     │     ├── Feed        → FeedScreen
 *     │     ├── Friends     → FriendListScreen
 *     │     ├── History     → HistoryScreen
 *     │     └── Settings    → SettingsScreen
 *     └── ForceLink         → ForceLinkScreen (modal)
 *
 * Design §4.1 (Auth init), §1.1 (navigation structure)
 */

import React, { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import AuthService from './src/services/AuthService';
import useAuthStore from './src/stores/useAuthStore';

import FeedScreen from './src/screens/FeedScreen';
import FriendListScreen from './src/screens/FriendListScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import ForceLinkScreen from './src/screens/auth/ForceLinkScreen';

// ---------------------------------------------------------------------------
// Navigator types
// ---------------------------------------------------------------------------

export type RootStackParamList = {
  MainTabs: undefined;
  ForceLink: undefined;
};

export type MainTabParamList = {
  Feed: undefined;
  Friends: undefined;
  History: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

// ---------------------------------------------------------------------------
// Tab icons (text emoji — replace with an icon library if desired)
// ---------------------------------------------------------------------------

const TAB_ICONS: Record<string, string> = {
  Feed: '🏠',
  Friends: '👥',
  History: '📋',
  Settings: '⚙️',
};

// ---------------------------------------------------------------------------
// Main tab navigator
// ---------------------------------------------------------------------------

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarActiveTintColor: '#ff6b6b',
        tabBarInactiveTintColor: '#888',
        tabBarLabel: route.name,
        tabBarIcon: ({ color }) => (
          // eslint-disable-next-line react-native/no-inline-styles
          <View style={{ opacity: color === '#ff6b6b' ? 1 : 0.5 }}>
            {/* Replace with vector icons when available */}
          </View>
        ),
      })}
    >
      <Tab.Screen
        name="Feed"
        component={FeedScreen}
        options={{ tabBarLabel: TAB_ICONS.Feed + ' Feed' }}
      />
      <Tab.Screen
        name="Friends"
        component={FriendListScreen}
        options={{ tabBarLabel: TAB_ICONS.Friends + ' Bạn bè' }}
      />
      <Tab.Screen
        name="History"
        component={HistoryScreen}
        options={{ tabBarLabel: TAB_ICONS.History + ' Lịch sử' }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ tabBarLabel: TAB_ICONS.Settings + ' Cài đặt' }}
      />
    </Tab.Navigator>
  );
}

// ---------------------------------------------------------------------------
// Root app
// ---------------------------------------------------------------------------

export default function App() {
  const [initialising, setInitialising] = useState(true);
  const { forceLinkRequired, setUser } = useAuthStore();

  useEffect(() => {
    AuthService.init()
      .then(() => {
        const user = AuthService.getCurrentUser();
        if (user) {
          setUser({ uid: user.uid, isAnonymous: user.isAnonymous });
        }
      })
      .finally(() => setInitialising(false));
  }, [setUser]);

  if (initialising) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color="#ff6b6b" />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          {forceLinkRequired ? (
            <Stack.Screen name="ForceLink" component={ForceLinkScreen} />
          ) : (
            <Stack.Screen name="MainTabs" component={MainTabs} />
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0f0f0f',
  },
  tabBar: {
    backgroundColor: '#111',
    borderTopColor: '#2a2a2a',
  },
});
