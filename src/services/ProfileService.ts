/**
 * ProfileService — backend API client for owner and pet profiles.
 *
 * All requests attach a Firebase ID token via AuthService.getIdToken()
 * (DL-F02-08). HTTP transport is global fetch.
 */

import AuthService from './AuthService';

const BASE_URL = 'http://localhost:8000';

export type PetSpecies = 'dog' | 'cat';
export type PetGender = 'male' | 'female' | 'unknown';

export interface OwnerProfile {
  userId: string;
  displayName: string | null;
  avatarUrl: string | null;
  isAnonymous: boolean;
  providers: string[];
}

export interface PatchOwnerProfileInput {
  displayName?: string | null;
  avatarUrl?: string | null;
}

export interface Pet {
  id: string;
  name: string;
  species: PetSpecies;
  gender: PetGender;
  birthdate: string | null;
  avatarUrl: string | null;
  createdAt: string;
}

export interface CreatePetInput {
  name: string;
  species: PetSpecies;
  gender?: PetGender;
  birthdate?: string | null;
  avatarUrl?: string | null;
}

export type PatchPetInput = Partial<CreatePetInput>;

export interface PresignedUrl {
  uploadUrl: string;
  objectKey: string;
  cdnUrl: string;
  expiresIn: number;
}

export interface PetPhoto {
  photoId: string;
  cdnUrl: string;
  takenAt: string | null;
}

export interface PetPhotosPage {
  petId: string;
  photos: PetPhoto[];
  nextCursor: string | null;
  hasMore: boolean;
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function parseOwnerProfile(data: any): OwnerProfile {
  return {
    userId: data.user_id,
    displayName: data.display_name,
    avatarUrl: data.avatar_url,
    isAnonymous: data.is_anonymous,
    providers: data.providers,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function parsePet(data: any): Pet {
  return {
    id: data.id,
    name: data.name,
    species: data.species,
    gender: data.gender,
    birthdate: data.birthdate ?? null,
    avatarUrl: data.avatar_url ?? null,
    createdAt: data.created_at,
  };
}

const ProfileService = {
  getOwnerProfile: async (): Promise<OwnerProfile> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/profile/me`, { headers });
    const data = await res.json();
    return parseOwnerProfile(data);
  },

  patchOwnerProfile: async (
    input: PatchOwnerProfileInput,
  ): Promise<OwnerProfile> => {
    const headers = await authHeaders();
    const body: Record<string, string | null> = {};
    if (input.displayName !== undefined) {
      body.display_name = input.displayName;
    }
    if (input.avatarUrl !== undefined) {
      body.avatar_url = input.avatarUrl;
    }
    const res = await fetch(`${BASE_URL}/profile/me`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return parseOwnerProfile(data);
  },

  getOwnerAvatarUploadUrl: async (
    contentType: string,
  ): Promise<PresignedUrl> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/profile/me/avatar/upload-url`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ content_type: contentType }),
    });
    const data = await res.json();
    return {
      uploadUrl: data.upload_url,
      objectKey: data.object_key,
      cdnUrl: data.cdn_url,
      expiresIn: data.expires_in,
    };
  },

  getPresignedUrl: async (
    scope: 'owner' | 'pet',
    contentType: string,
  ): Promise<PresignedUrl> => {
    const endpoint =
      scope === 'owner'
        ? '/profile/me/avatar/upload-url'
        : '/pets/avatar/upload-url';
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ content_type: contentType }),
    });
    const data = await res.json();
    return {
      uploadUrl: data.upload_url,
      objectKey: data.object_key,
      cdnUrl: data.cdn_url,
      expiresIn: data.expires_in,
    };
  },

  listPets: async (): Promise<Pet[]> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/pets`, { headers });
    const data = await res.json();
    return data.pets.map(parsePet);
  },

  createPet: async (input: CreatePetInput): Promise<Pet> => {
    const headers = await authHeaders();
    const body: Record<string, unknown> = {
      name: input.name,
      species: input.species,
    };
    if (input.gender !== undefined) {
      body.gender = input.gender;
    }
    if (input.birthdate !== undefined) {
      body.birthdate = input.birthdate;
    }
    if (input.avatarUrl !== undefined) {
      body.avatar_url = input.avatarUrl;
    }
    const res = await fetch(`${BASE_URL}/pets`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return parsePet(data);
  },

  getPet: async (petId: string): Promise<Pet> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/pets/${petId}`, { headers });
    const data = await res.json();
    return parsePet(data);
  },

  patchPet: async (petId: string, input: PatchPetInput): Promise<Pet> => {
    const headers = await authHeaders();
    const body: Record<string, unknown> = {};
    if (input.name !== undefined) {
      body.name = input.name;
    }
    if (input.species !== undefined) {
      body.species = input.species;
    }
    if (input.gender !== undefined) {
      body.gender = input.gender;
    }
    if (input.birthdate !== undefined) {
      body.birthdate = input.birthdate;
    }
    if (input.avatarUrl !== undefined) {
      body.avatar_url = input.avatarUrl;
    }
    const res = await fetch(`${BASE_URL}/pets/${petId}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return parsePet(data);
  },

  linkPhoto: async (petId: string, photoId: string): Promise<void> => {
    const headers = await authHeaders();
    await fetch(`${BASE_URL}/pets/${petId}/link-photo`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ photo_id: photoId }),
    });
  },

  getPetPhotos: async (
    petId: string,
    limit?: number,
    before?: string,
  ): Promise<PetPhotosPage> => {
    const headers = await authHeaders();
    const params = new URLSearchParams();
    if (limit !== undefined) {
      params.set('limit', String(limit));
    }
    if (before !== undefined) {
      params.set('before', before);
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(
      `${BASE_URL}/pets/${petId}/photos${query}`,
      { headers },
    );
    const data = await res.json();
    return {
      petId: data.pet_id,
      photos: data.photos.map(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (p: any) => ({
          photoId: p.photo_id,
          cdnUrl: p.cdn_url,
          takenAt: p.taken_at ?? null,
        }),
      ),
      nextCursor: data.next_cursor ?? null,
      hasMore: data.has_more,
    };
  },
};

export default ProfileService;
