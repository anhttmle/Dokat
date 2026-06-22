/**
 * Manual Jest mock for CaptureService.
 *
 * Activated via
 * ``jest.mock('../../services/capture/CaptureService')``.
 * ``process`` is a ``jest.fn()`` so tests can stub results.
 */

const CaptureService = {
  process: jest.fn(),
};

export default CaptureService;
