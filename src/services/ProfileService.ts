/**
 * ProfileService — backend API client for owner and pet profiles.
 *
 * Skeleton for F02 task 1.2; method bodies land in later tasks.
 * Mirrors the object-literal style of AuthService (Design §4.1).
 */

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

const NOT_IMPLEMENTED = 'ProfileService not implemented yet';

const ProfileService = {
  getOwnerProfile: async (): Promise<OwnerProfile> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  patchOwnerProfile: async (
    _input: PatchOwnerProfileInput,
  ): Promise<OwnerProfile> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  getPresignedUrl: async (
    _scope: 'owner' | 'pet',
    _contentType: string,
  ): Promise<PresignedUrl> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  listPets: async (): Promise<Pet[]> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  createPet: async (_input: CreatePetInput): Promise<Pet> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  getPet: async (_petId: string): Promise<Pet> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  patchPet: async (
    _petId: string,
    _input: PatchPetInput,
  ): Promise<Pet> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  linkPhoto: async (_petId: string, _photoId: string): Promise<void> => {
    throw new Error(NOT_IMPLEMENTED);
  },

  getPetPhotos: async (
    _petId: string,
    _limit?: number,
    _before?: string,
  ): Promise<PetPhotosPage> => {
    throw new Error(NOT_IMPLEMENTED);
  },
};

export default ProfileService;
