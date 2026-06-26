/**
 * ReportDialog — pick a fixed reason and report a user.
 *
 * Offers the four fixed reasons (DL-F10-06), calls
 * SettingsService.reportUser, then shows a confirmation. Reporting never
 * blocks or hides the reported user (AC-F10-5).
 *
 * Refs: Design §1.4, §4.2; FR-6; AC-F10-5; DL-F10-06
 */

import React from 'react';
import { Modal, Text, TouchableOpacity, View } from 'react-native';

import SettingsService, {
  ReportReason,
} from '../services/SettingsService';

interface Props {
  visible: boolean;
  userId: string;
  onClose: () => void;
}

const REASONS: { value: ReportReason; label: string }[] = [
  { value: 'spam', label: 'Spam' },
  { value: 'inappropriate', label: 'Nội dung không phù hợp' },
  { value: 'harassment', label: 'Quấy rối' },
  { value: 'other', label: 'Khác' },
];

const ReportDialog: React.FC<Props> = ({ visible, userId, onClose }) => {
  const [selected, setSelected] = React.useState<ReportReason | null>(null);
  const [submitted, setSubmitted] = React.useState(false);

  const handleSubmit = React.useCallback(async () => {
    if (selected === null) {
      return;
    }
    await SettingsService.reportUser(userId, selected);
    setSubmitted(true);
  }, [selected, userId]);

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View testID="report-dialog">
        {submitted ? (
          <View>
            <Text>Cảm ơn bạn đã báo cáo</Text>
            <TouchableOpacity testID="report-close" onPress={onClose}>
              <Text>Đóng</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View>
            <Text>Báo cáo người dùng</Text>
            {REASONS.map((r) => (
              <TouchableOpacity
                key={r.value}
                testID={`reason-${r.value}`}
                onPress={() => setSelected(r.value)}
              >
                <Text>
                  {selected === r.value ? `✓ ${r.label}` : r.label}
                </Text>
              </TouchableOpacity>
            ))}
            <TouchableOpacity
              testID="report-submit"
              onPress={handleSubmit}
            >
              <Text>Gửi báo cáo</Text>
            </TouchableOpacity>
            <TouchableOpacity testID="report-cancel" onPress={onClose}>
              <Text>Hủy</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </Modal>
  );
};

export default ReportDialog;
