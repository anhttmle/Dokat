/**
 * NotificationPreferenceSection — 4 toggle rows for reminder types.
 *
 * Rendered inside SettingsScreen (F10); F09 is the owner of this
 * component and the backend preferences API (DL-F09-03).
 *
 * Refs: Design §2.5, §4.2; AC-F09-4, AC-F09-5
 */

import React from 'react';
import { Switch, Text, View } from 'react-native';

import {
  NotificationPreferences,
  ReminderType,
} from '../services/NotificationService';

const REMINDER_LABELS: Record<ReminderType, string> = {
  feeding: 'Cho ăn',
  sleeping: 'Ngủ',
  bathing: 'Tắm',
  playing: 'Chơi',
};

const REMINDER_ORDER: ReminderType[] = [
  'feeding',
  'sleeping',
  'bathing',
  'playing',
];

export interface NotificationPreferenceSectionProps {
  preferences: NotificationPreferences;
  onToggle: (type: ReminderType, enabled: boolean) => void;
}

/**
 * Renders four toggle rows, one per reminder type, using the
 * Vietnamese labels defined in Design §2.5.
 */
export function NotificationPreferenceSection({
  preferences,
  onToggle,
}: NotificationPreferenceSectionProps): React.ReactElement {
  return (
    <View>
      {REMINDER_ORDER.map((type) => (
        <View
          key={type}
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingVertical: 12,
            paddingHorizontal: 16,
          }}
        >
          <Text>{REMINDER_LABELS[type]}</Text>
          <Switch
            value={preferences[type]}
            onValueChange={(value) => onToggle(type, value)}
            testID={`toggle-${type}`}
            accessibilityLabel={REMINDER_LABELS[type]}
          />
        </View>
      ))}
    </View>
  );
}
