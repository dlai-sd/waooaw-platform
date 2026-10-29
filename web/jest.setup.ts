import '@testing-library/jest-dom';

jest.mock('server-only', () => ({}));

if (!globalThis.crypto.randomUUID) {
  Object.defineProperty(globalThis.crypto, 'randomUUID', {
    configurable: true,
    value: () => '00000000-0000-4000-8000-000000000000',
  });
}
