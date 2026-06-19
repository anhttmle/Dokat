/**
 * LinkAccountSheet — bottom sheet shown when a Guest User triggers
 * an action that requires a linked account (AC-F01-2, AC-F01-3).
 *
 * OAuth provider buttons (Apple / Google / Facebook) implemented in task 3.
 */

import React from 'react';
import { Modal, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

interface Props {
  visible: boolean;
  onDismiss: () => void;
  onLinked: () => void;
}

const LinkAccountSheet: React.FC<Props> = ({ visible, onDismiss }) => (
  <Modal
    animationType="slide"
    onRequestClose={onDismiss}
    transparent
    visible={visible}
  >
    <View style={styles.backdrop}>
      <View style={styles.sheet}>
        <Text style={styles.title}>Link your account</Text>
        <Text style={styles.subtitle}>
          Sign in with Apple, Google, or Facebook to continue.
        </Text>
        {/* OAuth provider buttons — implemented in task 3 */}
        <TouchableOpacity onPress={onDismiss} style={styles.cancelButton}>
          <Text>Cancel</Text>
        </TouchableOpacity>
      </View>
    </View>
  </Modal>
);

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
