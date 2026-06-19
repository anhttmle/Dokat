/**
 * ForceLinkScreen — full-screen, non-dismissible screen shown when
 * forceLinkRequired is true (AC-F01-4, Design §4.1).
 *
 * Buttons (Apple / Google / Facebook) are implemented in task 3.
 */

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

const ForceLinkScreen: React.FC = () => (
  <View style={styles.container} testID="force-link-screen">
    <Text style={styles.title}>Link your account to continue</Text>
    <Text style={styles.subtitle}>
      Your guest account has expired. Link with Apple, Google, or Facebook to
      keep your data.
    </Text>
    {/* OAuth provider buttons — implemented in task 3 */}
  </View>
);

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    padding: 24,
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
