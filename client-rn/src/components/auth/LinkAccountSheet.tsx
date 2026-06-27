/**
 * LinkAccountSheet — bottom sheet shown when a Guest User triggers
 * an action that requires a linked account (AC-F01-2, AC-F01-3).
 *
 * Renders three OAuth provider buttons (Apple / Google / Facebook).
 * Each tap calls ``AuthService.linkWithProvider(provider)`` and fires
 * ``onLinked`` on success.  Returns null when ``visible`` is false so
 * that test assertions can use ``queryByTestId``.
 */

import React from 'react';
import {
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import AuthService from '../../services/AuthService';

interface Props {
  visible: boolean;
  onDismiss: () => void;
  onLinked: () => void;
}

const PROVIDERS = [
  { id: 'apple', label: 'Apple' },
  { id: 'google', label: 'Google' },
  { id: 'facebook', label: 'Facebook' },
] as const;

const LinkAccountSheet: React.FC<Props> = ({
  visible,
  onDismiss,
  onLinked,
}) => {
  if (!visible) return null;

  const handleProviderTap = async (provider: string): Promise<void> => {
    await AuthService.linkWithProvider(provider);
    onLinked();
  };

  return (
    <Modal
      animationType="slide"
      onRequestClose={onDismiss}
      transparent
      visible={visible}
    >
      <View style={styles.backdrop}>
        <View style={styles.sheet} testID="link-account-sheet">
          <Text style={styles.title}>Link your account</Text>
          <Text style={styles.subtitle}>
            Sign in with Apple, Google, or Facebook to continue.
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
          <TouchableOpacity
            onPress={onDismiss}
            style={styles.cancelButton}
            testID="cancel"
          >
            <Text>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: 'rgba(0,0,0,0.4)',
    flex: 1,
    justifyContent: 'flex-end',
  },
  cancelButton: {
    alignItems: 'center',
    marginTop: 16,
    padding: 12,
  },
  providerButton: {
    alignItems: 'center',
    borderRadius: 8,
    marginTop: 12,
    padding: 14,
  },
  providerLabel: {
    fontSize: 16,
    fontWeight: '600',
  },
  sheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 24,
  },
  subtitle: {
    fontSize: 14,
    marginTop: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
  },
});

export default LinkAccountSheet;
