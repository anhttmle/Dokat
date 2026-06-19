/**
 * Manual mock for @react-native-async-storage/async-storage
 * All methods return resolved promises to simulate async storage.
 */

const storage = {};

const AsyncStorage = {
  setItem: jest.fn((key, value) => {
    storage[key] = value;
    return Promise.resolve();
  }),
  getItem: jest.fn((key) => Promise.resolve(storage[key] ?? null)),
  removeItem: jest.fn((key) => {
    delete storage[key];
    return Promise.resolve();
  }),
  multiRemove: jest.fn((keys) => {
    keys.forEach((key) => delete storage[key]);
    return Promise.resolve();
  }),
  clear: jest.fn(() => {
    Object.keys(storage).forEach((key) => delete storage[key]);
    return Promise.resolve();
  }),
};

module.exports = AsyncStorage;
module.exports.default = AsyncStorage;
