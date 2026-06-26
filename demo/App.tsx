/**
 * Dokat — Demo App (Expo Web)
 *
 * Standalone demo chạy trên trình duyệt bằng Expo Web.
 * Mock data, không kết nối backend thực.
 *
 * 4 tab: Feed | Kết bạn | Lịch sử | Cài đặt
 */

import { StatusBar } from 'expo-status-bar';
import React, { useState } from 'react';
import {
  FlatList,
  Image,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

type ReminderKey = 'feeding' | 'sleeping' | 'bathing' | 'playing';

interface FeedPost {
  id: string;
  senderName: string;
  petName: string;
  imageUrl: string;
  createdAt: string;
  seen: boolean;
}

interface Friend {
  id: string;
  name: string;
  petName: string;
  avatarUrl: string;
}

const MOCK_FEED: FeedPost[] = [
  {
    id: '1',
    senderName: 'Minh Anh',
    petName: 'Bông',
    imageUrl: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400',
    createdAt: '2026-06-25T14:00:00Z',
    seen: false,
  },
  {
    id: '2',
    senderName: 'Quốc Huy',
    petName: 'Mochi',
    imageUrl: 'https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=400',
    createdAt: '2026-06-25T11:30:00Z',
    seen: false,
  },
  {
    id: '3',
    senderName: 'Lan Phương',
    petName: 'Caramel',
    imageUrl: 'https://images.unsplash.com/photo-1548681528-6a5c45b66b42?w=400',
    createdAt: '2026-06-24T20:00:00Z',
    seen: true,
  },
  {
    id: '4',
    senderName: 'Tuấn Kiệt',
    petName: 'Shiro',
    imageUrl: 'https://images.unsplash.com/photo-1513360371669-4adf3dd7dff8?w=400',
    createdAt: '2026-06-24T09:00:00Z',
    seen: true,
  },
];

const MOCK_FRIENDS: Friend[] = [
  { id: 'f1', name: 'Minh Anh', petName: 'Bông (Golden Retriever)', avatarUrl: 'https://i.pravatar.cc/60?img=1' },
  { id: 'f2', name: 'Quốc Huy', petName: 'Mochi (Corgi)', avatarUrl: 'https://i.pravatar.cc/60?img=2' },
  { id: 'f3', name: 'Lan Phương', petName: 'Caramel (Mèo Anh lông ngắn)', avatarUrl: 'https://i.pravatar.cc/60?img=3' },
  { id: 'f4', name: 'Tuấn Kiệt', petName: 'Shiro (Mèo Munchkin)', avatarUrl: 'https://i.pravatar.cc/60?img=4' },
  { id: 'f5', name: 'Bảo Ngọc', petName: 'Mèo tam thể', avatarUrl: 'https://i.pravatar.cc/60?img=5' },
];

const MOCK_HISTORY_SENT = [
  { id: 'h1', petName: 'Lucky', imageUrl: 'https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=200', sentTo: 3, createdAt: '2026-06-25T08:00:00Z' },
  { id: 'h2', petName: 'Lucky', imageUrl: 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=200', sentTo: 5, createdAt: '2026-06-24T16:00:00Z' },
];

const MOCK_HISTORY_RECEIVED = [
  { id: 'hr1', senderName: 'Minh Anh', petName: 'Bông', imageUrl: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=200', createdAt: '2026-06-25T14:00:00Z' },
  { id: 'hr2', senderName: 'Quốc Huy', petName: 'Mochi', imageUrl: 'https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=200', createdAt: '2026-06-25T11:30:00Z' },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3600000);
  if (h < 1) return 'vừa xong';
  if (h < 24) return `${h}h trước`;
  return `${Math.floor(h / 24)}d trước`;
}

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

const C = {
  bg: '#0f0f0f',
  card: '#1a1a1a',
  border: '#2a2a2a',
  accent: '#ff6b6b',
  text: '#ffffff',
  muted: '#888',
  tab: '#111',
  tabActive: '#ff6b6b',
};

// ---------------------------------------------------------------------------
// FeedScreen
// ---------------------------------------------------------------------------

function FeedScreen() {
  const [items, setItems] = useState<FeedPost[]>(MOCK_FEED);
  const [selected, setSelected] = useState<FeedPost | null>(null);

  function openPost(post: FeedPost) {
    setSelected(post);
    setItems(prev =>
      prev.map(p => p.id === post.id ? { ...p, seen: true } : p),
    );
  }

  return (
    <View style={s.flex}>
      <View style={s.header}>
        <Text style={s.headerTitle}>🐾 Dokat</Text>
      </View>
      <FlatList
        data={items}
        keyExtractor={i => i.id}
        contentContainerStyle={s.feedList}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[s.feedCard, !item.seen && s.feedCardUnseen]}
            onPress={() => openPost(item)}
            activeOpacity={0.85}
          >
            <Image source={{ uri: item.imageUrl }} style={s.feedImage} />
            {!item.seen && <View style={s.unseenBadge}><Text style={s.unseenBadgeText}>MỚI</Text></View>}
            <View style={s.feedMeta}>
              <View>
                <Text style={s.feedSender}>{item.senderName}</Text>
                <Text style={s.feedPet}>🐶 {item.petName}</Text>
              </View>
              <Text style={s.feedTime}>{relativeTime(item.createdAt)}</Text>
            </View>
          </TouchableOpacity>
        )}
      />

      <Modal visible={!!selected} transparent animationType="fade">
        <View style={s.modalOverlay}>
          <TouchableOpacity style={s.modalClose} onPress={() => setSelected(null)}>
            <Text style={s.modalCloseText}>✕</Text>
          </TouchableOpacity>
          {selected && (
            <View style={s.modalCard}>
              <Image source={{ uri: selected.imageUrl }} style={s.modalImage} />
              <Text style={s.modalSender}>{selected.senderName} · {selected.petName}</Text>
              <Text style={s.feedTime}>{relativeTime(selected.createdAt)}</Text>
            </View>
          )}
        </View>
      </Modal>
    </View>
  );
}

// ---------------------------------------------------------------------------
// FriendsScreen
// ---------------------------------------------------------------------------

function FriendsScreen() {
  const [showQR, setShowQR] = useState(false);

  return (
    <View style={s.flex}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Bạn bè</Text>
        <TouchableOpacity style={s.qrBtn} onPress={() => setShowQR(true)}>
          <Text style={s.qrBtnText}>+ Thêm bạn</Text>
        </TouchableOpacity>
      </View>
      <ScrollView contentContainerStyle={s.list}>
        {MOCK_FRIENDS.map(f => (
          <View key={f.id} style={s.friendRow}>
            <Image source={{ uri: f.avatarUrl }} style={s.avatar} />
            <View style={s.flex}>
              <Text style={s.friendName}>{f.name}</Text>
              <Text style={s.friendPet}>{f.petName}</Text>
            </View>
          </View>
        ))}
      </ScrollView>

      <Modal visible={showQR} transparent animationType="slide">
        <View style={s.modalOverlay}>
          <View style={s.qrModal}>
            <Text style={s.qrTitle}>Mã QR của bạn</Text>
            <View style={s.qrBox}>
              {/* QR pattern placeholder */}
              {Array.from({ length: 7 }).map((_, row) => (
                <View key={row} style={s.qrRow}>
                  {Array.from({ length: 7 }).map((__, col) => (
                    <View
                      key={col}
                      style={[
                        s.qrCell,
                        (row < 2 || col < 2 || (row > 4 && col > 4))
                          ? s.qrCellDark
                          : Math.random() > 0.5 ? s.qrCellDark : s.qrCellLight,
                      ]}
                    />
                  ))}
                </View>
              ))}
            </View>
            <Text style={s.qrSub}>Cho bạn bè quét để kết bạn · hết hạn sau 5 phút</Text>
            <TouchableOpacity style={s.closeBtn} onPress={() => setShowQR(false)}>
              <Text style={s.closeBtnText}>Đóng</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// ---------------------------------------------------------------------------
// HistoryScreen
// ---------------------------------------------------------------------------

function HistoryScreen() {
  const [tab, setTab] = useState<'sent' | 'received'>('sent');

  const data = tab === 'sent' ? MOCK_HISTORY_SENT : MOCK_HISTORY_RECEIVED;

  return (
    <View style={s.flex}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Lịch sử</Text>
      </View>
      <View style={s.segRow}>
        <TouchableOpacity
          style={[s.segBtn, tab === 'sent' && s.segBtnActive]}
          onPress={() => setTab('sent')}
        >
          <Text style={[s.segText, tab === 'sent' && s.segTextActive]}>Đã gửi</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[s.segBtn, tab === 'received' && s.segBtnActive]}
          onPress={() => setTab('received')}
        >
          <Text style={[s.segText, tab === 'received' && s.segTextActive]}>Đã nhận</Text>
        </TouchableOpacity>
      </View>
      <FlatList
        data={data}
        keyExtractor={i => i.id}
        numColumns={2}
        contentContainerStyle={s.historyGrid}
        renderItem={({ item }) => (
          <View style={s.historyCard}>
            <Image source={{ uri: item.imageUrl }} style={s.historyImage} />
            {'sentTo' in item
              ? <Text style={s.historyMeta}>Gửi cho {item.sentTo} người · {relativeTime(item.createdAt)}</Text>
              : <Text style={s.historyMeta}>{(item as { senderName: string }).senderName} · {relativeTime(item.createdAt)}</Text>
            }
          </View>
        )}
      />
    </View>
  );
}

// ---------------------------------------------------------------------------
// SettingsScreen
// ---------------------------------------------------------------------------

const REMINDER_LABELS: Record<ReminderKey, string> = {
  feeding: 'Cho ăn',
  sleeping: 'Ngủ',
  bathing: 'Tắm',
  playing: 'Chơi',
};

function SettingsScreen() {
  const [prefs, setPrefs] = useState<Record<ReminderKey, boolean>>({
    feeding: true, sleeping: true, bathing: true, playing: true,
  });

  function toggle(key: ReminderKey) {
    setPrefs(p => ({ ...p, [key]: !p[key] }));
  }

  return (
    <ScrollView style={s.flex} contentContainerStyle={s.list}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Cài đặt</Text>
      </View>

      {/* Profile section */}
      <View style={s.settingsSection}>
        <View style={s.profileRow}>
          <Image
            source={{ uri: 'https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=80' }}
            style={s.profileAvatar}
          />
          <View>
            <Text style={s.profileName}>Nguyễn Demo</Text>
            <Text style={s.muted}>Chủ của Lucky 🐕</Text>
          </View>
        </View>
      </View>

      {/* Account providers */}
      <Text style={s.sectionLabel}>TÀI KHOẢN</Text>
      <View style={s.settingsSection}>
        {['Google', 'Apple', 'Facebook'].map(p => (
          <View key={p} style={s.settingsRow}>
            <Text style={s.settingsRowLabel}>{p}</Text>
            <Text style={s.settingsRowValue}>Liên kết</Text>
          </View>
        ))}
      </View>

      {/* Reminder preferences */}
      <Text style={s.sectionLabel}>NHẮC NHỞ THÚ CƯNG</Text>
      <View style={s.settingsSection}>
        {(Object.keys(REMINDER_LABELS) as ReminderKey[]).map(key => (
          <View key={key} style={s.settingsRow}>
            <Text style={s.settingsRowLabel}>{REMINDER_LABELS[key]}</Text>
            <Switch
              value={prefs[key]}
              onValueChange={() => toggle(key)}
              trackColor={{ false: C.border, true: C.accent }}
              thumbColor="#fff"
            />
          </View>
        ))}
      </View>

      {/* Danger zone */}
      <Text style={s.sectionLabel}>KHÁC</Text>
      <View style={s.settingsSection}>
        <TouchableOpacity style={s.settingsRow}>
          <Text style={[s.settingsRowLabel, { color: '#ff9944' }]}>Báo cáo người dùng</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.settingsRow}>
          <Text style={[s.settingsRowLabel, { color: C.accent }]}>Đăng xuất</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

// ---------------------------------------------------------------------------
// Tab bar
// ---------------------------------------------------------------------------

type Tab = 'feed' | 'friends' | 'history' | 'settings';

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'feed', label: 'Feed', icon: '🏠' },
  { key: 'friends', label: 'Bạn bè', icon: '👥' },
  { key: 'history', label: 'Lịch sử', icon: '📋' },
  { key: 'settings', label: 'Cài đặt', icon: '⚙️' },
];

function TabBar({
  active,
  onSelect,
}: {
  active: Tab;
  onSelect: (t: Tab) => void;
}) {
  return (
    <View style={s.tabBar}>
      {TABS.map(t => (
        <TouchableOpacity
          key={t.key}
          style={s.tabItem}
          onPress={() => onSelect(t.key)}
        >
          <Text style={[s.tabIcon, active === t.key && s.tabIconActive]}>
            {t.icon}
          </Text>
          <Text style={[s.tabLabel, active === t.key && s.tabLabelActive]}>
            {t.label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Root App
// ---------------------------------------------------------------------------

export default function App() {
  const [tab, setTab] = useState<Tab>('feed');

  return (
    <View style={s.root}>
      <StatusBar style="light" />
      <View style={s.phone}>
        <View style={s.screen}>
          {tab === 'feed' && <FeedScreen />}
          {tab === 'friends' && <FriendsScreen />}
          {tab === 'history' && <HistoryScreen />}
          {tab === 'settings' && <SettingsScreen />}
        </View>
        <TabBar active={tab} onSelect={setTab} />
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const isWeb = Platform.OS === 'web';

const s = StyleSheet.create({
  flex: { flex: 1 },

  root: {
    flex: 1,
    backgroundColor: '#060606',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: isWeb ? ('100vh' as unknown as number) : undefined,
  },

  phone: {
    width: isWeb ? 390 : '100%' as unknown as number,
    height: isWeb ? 844 : '100%' as unknown as number,
    backgroundColor: C.bg,
    borderRadius: isWeb ? 40 : 0,
    overflow: 'hidden',
    ...(isWeb && {
      boxShadow: '0 32px 80px rgba(0,0,0,0.8)',
    } as object),
    flex: 1,
    maxHeight: isWeb ? 844 : undefined,
  },

  screen: {
    flex: 1,
    backgroundColor: C.bg,
    overflow: 'hidden',
  },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 52,
    paddingBottom: 12,
    backgroundColor: C.bg,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  headerTitle: {
    color: C.text,
    fontSize: 22,
    fontWeight: '700',
  },

  // Feed
  feedList: { padding: 12, gap: 12 },
  feedCard: {
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.border,
  },
  feedCardUnseen: {
    borderColor: C.accent,
    borderWidth: 2,
  },
  feedImage: {
    width: '100%' as unknown as number,
    height: 260,
    backgroundColor: '#222',
  },
  feedMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
  },
  feedSender: { color: C.text, fontWeight: '600', fontSize: 15 },
  feedPet: { color: C.muted, fontSize: 13, marginTop: 2 },
  feedTime: { color: C.muted, fontSize: 12 },
  unseenBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
    backgroundColor: C.accent,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  unseenBadgeText: { color: '#fff', fontSize: 11, fontWeight: '700' },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.92)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalClose: {
    position: 'absolute',
    top: 52,
    right: 20,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: C.card,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  modalCloseText: { color: C.text, fontSize: 18 },
  modalCard: {
    width: 340,
    borderRadius: 20,
    overflow: 'hidden',
    backgroundColor: C.card,
  },
  modalImage: { width: '100%' as unknown as number, height: 400 },
  modalSender: {
    color: C.text,
    fontWeight: '600',
    fontSize: 16,
    padding: 12,
  },

  // Friends
  list: { padding: 12, gap: 0 },
  friendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  avatar: { width: 48, height: 48, borderRadius: 24 },
  friendName: { color: C.text, fontWeight: '600', fontSize: 15 },
  friendPet: { color: C.muted, fontSize: 13, marginTop: 2 },

  qrBtn: {
    backgroundColor: C.accent,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  qrBtnText: { color: '#fff', fontWeight: '600', fontSize: 14 },

  qrModal: {
    width: 300,
    backgroundColor: C.card,
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    gap: 16,
  },
  qrTitle: { color: C.text, fontSize: 18, fontWeight: '700' },
  qrBox: { gap: 2 },
  qrRow: { flexDirection: 'row', gap: 2 },
  qrCell: { width: 30, height: 30, borderRadius: 4 },
  qrCellDark: { backgroundColor: C.text },
  qrCellLight: { backgroundColor: C.border },
  qrSub: { color: C.muted, fontSize: 12, textAlign: 'center' },
  closeBtn: {
    backgroundColor: C.border,
    borderRadius: 12,
    paddingHorizontal: 24,
    paddingVertical: 10,
  },
  closeBtnText: { color: C.text, fontWeight: '600' },

  // History
  segRow: {
    flexDirection: 'row',
    margin: 12,
    backgroundColor: C.card,
    borderRadius: 12,
    padding: 4,
  },
  segBtn: { flex: 1, paddingVertical: 8, borderRadius: 10, alignItems: 'center' },
  segBtnActive: { backgroundColor: C.accent },
  segText: { color: C.muted, fontWeight: '600' },
  segTextActive: { color: '#fff' },
  historyGrid: { padding: 8, gap: 8 },
  historyCard: {
    flex: 1,
    margin: 4,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: C.card,
  },
  historyImage: { width: '100%' as unknown as number, height: 160 },
  historyMeta: { color: C.muted, fontSize: 11, padding: 8 },

  // Settings
  sectionLabel: {
    color: C.muted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1,
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 6,
  },
  settingsSection: {
    backgroundColor: C.card,
    marginHorizontal: 12,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: C.border,
  },
  settingsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  settingsRowLabel: { color: C.text, fontSize: 15 },
  settingsRowValue: { color: C.muted, fontSize: 14 },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 16,
  },
  profileAvatar: { width: 56, height: 56, borderRadius: 28 },
  profileName: { color: C.text, fontWeight: '700', fontSize: 17 },
  muted: { color: C.muted, fontSize: 13, marginTop: 2 },

  // Tab bar
  tabBar: {
    flexDirection: 'row',
    backgroundColor: C.tab,
    borderTopWidth: 1,
    borderTopColor: C.border,
    paddingBottom: isWeb ? 8 : 16,
    paddingTop: 8,
  },
  tabItem: { flex: 1, alignItems: 'center', gap: 2 },
  tabIcon: { fontSize: 22, opacity: 0.4 },
  tabIconActive: { opacity: 1 },
  tabLabel: { color: C.muted, fontSize: 10 },
  tabLabelActive: { color: C.tabActive, fontWeight: '600' },
});
