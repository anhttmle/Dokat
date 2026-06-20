/**
 * ForceLinkScreen — full-screen, non-dismissible screen shown when
 * forceLinkRequired is true (AC-F01-4, Design §4.1).
 *
 * Back navigation is blocked via the beforeRemove listener so the user
 * cannot dismiss this screen without linking an OAuth account.
 */

import React, { useEffect } from 'react';
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';

import AuthService from '../../services/AuthService';
import useAuthStore from '../../stores/useAuthStore';

const PROVIDERS = [
  { id: 'apple', label: 'Continue with Apple' },
  { id: 'google', label: 'Continue with Google' },
  { id: 'facebook', label: 'Continue with Facebook' },
] as const;

const ForceLinkScreen: React.FC = () => {
  const navigation = useNavigation();
  const { setForceLinkRequired } = useAuthStore();

  useEffect(() => {
    const unsubscribe = navigation.addListener(
      'beforeRemove',
      (e: { preventDefault: () => void }) => {
        e.preventDefault();
      },
    );
    return unsubscribe;
  }, [navigation]);

  const handleProviderTap = async (provider: string): Promise<void> => {
    await AuthService.linkWithProvider(provider);
    setForceLinkRequired(false);
  };

  return (
    <View style={styles.container} testID="force-link-screen">
      <Text style={styles.title}>Link your account to continue</Text>
      <Text style={styles.subtitle}>
        Your guest account has expired. Link with Apple, Google, or
        Facebook to keep your data.
      </Text>
      {PROVIDERS.map(({ id, label }) => (
        <TouchableOpacity
          key={id}
          onPress={() => handleProviderTap(id)}
          style={styles.providerButton}
          testID={`provider-${id}`}
        >
          <Text style={styles.providerLabel}>{label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  providerButton: {
    alignItems: 'center',
    borderRadius: 8,
    marginTop: 12,
    padding: 14,
    width: '100%',
  },
  providerLabel: {
    fontSize: 16,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
  },
});

export default ForceLinkScreen;
