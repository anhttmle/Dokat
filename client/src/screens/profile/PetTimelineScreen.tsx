/**
 * PetTimelineScreen — infinite-scroll photo timeline for one pet.
 *
 * Receives `pet` via route.params (Design §4.1, §3.10).
 * Loads photos through ProfileService.getPetPhotos with cursor
 * pagination (next_cursor / before param).
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  Text,
  View,
} from 'react-native';

import { useRoute } from '@react-navigation/native';

import ProfileService, {
  Pet,
  PetPhoto,
} from '../../services/ProfileService';

interface RouteParams {
  pet: Pet;
}

const PetTimelineScreen: React.FC = () => {
  const route = useRoute();
  const { pet } = route.params as RouteParams;

  const [photos, setPhotos] = useState<PetPhoto[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  const loadPage = useCallback(
    async (before?: string) => {
      if (loading) {
        return;
      }
      setLoading(true);
      try {
        const page = await ProfileService.getPetPhotos(
          pet.id,
          undefined,
          before,
        );
        setPhotos(prev =>
          before ? [...prev, ...page.photos] : page.photos,
        );
        setNextCursor(page.nextCursor);
        setHasMore(page.hasMore);
      } finally {
        setLoading(false);
      }
    },
    [pet.id, loading],
  );

  useEffect(() => {
    loadPage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleEndReached = () => {
    if (hasMore && !loading && nextCursor) {
      loadPage(nextCursor);
    }
  };

  return (
    <View testID="pet-timeline-screen">
      <View testID="pet-timeline-header">
        {pet.avatarUrl ? (
          <Image
            testID="pet-timeline-avatar"
            source={{ uri: pet.avatarUrl }}
            style={{ width: 60, height: 60, borderRadius: 30 }}
          />
        ) : null}
        <Text testID="pet-timeline-name">{pet.name}</Text>
      </View>

      <FlatList
        testID="pet-timeline-list"
        data={photos}
        numColumns={2}
        keyExtractor={item => item.photoId}
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.5}
        ListFooterComponent={
          loading && hasMore ? <ActivityIndicator testID="loading-spinner" /> : null
        }
        renderItem={({ item }) => (
          <Image
            testID="timeline-photo-item"
            source={{ uri: item.cdnUrl }}
            style={{ width: '50%', aspectRatio: 1 }}
          />
        )}
      />
    </View>
  );
};

export default PetTimelineScreen;
