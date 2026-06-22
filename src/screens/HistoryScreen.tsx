/**
 * HistoryScreen — the 24h timeline of sent + received photos (F08).
 *
 * On mount it loads both sections in parallel via HistoryService.getSent()
 * and getReceived() (FR-1) and renders them through HistoryList ("Đã gửi"
 * / "Đã nhận" — FR-3). Pull-to-refresh reloads both (Technical
 * Constraint). When both sections are empty it shows an empty state
 * (FR-6). Tapping a photo opens it full-screen (FR-5): a sent photo
 * fetches SeenService.getSeenBy() and renders <SeenByList/> (DL-F08-08);
 * a received photo calls SeenService.markSeen() (idempotent — F07).
 *
 * Refs: Design §1.1, §1.3, §1.4, §4.2; FR-1, FR-3, FR-5, FR-6;
 *       AC-F08-2, AC-F08-3, AC-F08-4; DL-F08-08
 */

import React from 'react';
import {
  Modal,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import HistoryList from '../components/HistoryList';
import SeenByList from '../components/SeenByList';
import HistoryService, {
  ReceivedHistoryItem,
  SentHistoryItem,
} from '../services/HistoryService';
import SeenService, { SeenByResult } from '../services/SeenService';

const HistoryScreen: React.FC = () => {
  const [sent, setSent] = React.useState<SentHistoryItem[]>([]);
  const [received, setReceived] = React.useState<ReceivedHistoryItem[]>([]);
  const [refreshing, setRefreshing] = React.useState(false);
  const [openSent, setOpenSent] = React.useState<SentHistoryItem | null>(
    null,
  );
  const [openReceived, setOpenReceived] =
    React.useState<ReceivedHistoryItem | null>(null);
  const [seenBy, setSeenBy] = React.useState<SeenByResult | null>(null);

  const load = React.useCallback(async () => {
    const [sentResult, receivedResult] = await Promise.all([
      HistoryService.getSent(),
      HistoryService.getReceived(),
    ]);
    setSent(sentResult.items);
    setReceived(receivedResult.items);
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  const handleRefresh = React.useCallback(async () => {
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  const handleOpenSent = React.useCallback(async (item: SentHistoryItem) => {
    setOpenSent(item);
    setSeenBy(null);
    const result = await SeenService.getSeenBy(item.post_id);
    setSeenBy(result);
  }, []);

  const handleOpenReceived = React.useCallback(
    (item: ReceivedHistoryItem) => {
      setOpenReceived(item);
      setReceived((prev) =>
        prev.map((it) =>
          it.post_id === item.post_id ? { ...it, seen: true } : it,
        ),
      );
      SeenService.markSeen(item.post_id);
    },
    [],
  );

  const closeModal = React.useCallback(() => {
    setOpenSent(null);
    setOpenReceived(null);
    setSeenBy(null);
  }, []);

  const isEmpty = sent.length === 0 && received.length === 0;

  return (
    <View testID="history-screen" style={{ flex: 1 }}>
      <ScrollView
        testID="history-scroll"
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
          />
        }
      >
        {isEmpty ? (
          <View testID="history-empty-state">
            <Text>Chưa có ảnh nào trong 24 giờ qua</Text>
          </View>
        ) : (
          <>
            <HistoryList
              title="Đã gửi"
              mode="sent"
              items={sent}
              onOpen={handleOpenSent}
            />
            <HistoryList
              title="Đã nhận"
              mode="received"
              items={received}
              onOpen={handleOpenReceived}
            />
          </>
        )}
      </ScrollView>

      <Modal
        visible={openSent !== null || openReceived !== null}
        transparent
        onRequestClose={closeModal}
      >
        <View testID="history-fullscreen" style={{ flex: 1 }}>
          {openReceived ? (
            <Text testID="fullscreen-sender">
              {openReceived.sender_display_name ?? 'Người dùng'}
            </Text>
          ) : null}
          {openSent && seenBy ? <SeenByList result={seenBy} /> : null}
          <TouchableOpacity testID="fullscreen-close" onPress={closeModal}>
            <Text>Đóng</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  );
};

export default HistoryScreen;
