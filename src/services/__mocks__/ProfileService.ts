/**
 * Manual Jest mock for ProfileService.
 *
 * Activated in tests via ``jest.mock('../../services/ProfileService')``.
 * Every method is a ``jest.fn()`` so tests can stub return values.
 */

const ProfileService = {
  getOwnerProfile: jest.fn(),
  patchOwnerProfile: jest.fn(),
  getOwnerAvatarUploadUrl: jest.fn(),
  getPresignedUrl: jest.fn(),
  listPets: jest.fn(),
  createPet: jest.fn(),
  getPet: jest.fn(),
  patchPet: jest.fn(),
  linkPhoto: jest.fn(),
  getPetPhotos: jest.fn(),
};

export default ProfileService;
