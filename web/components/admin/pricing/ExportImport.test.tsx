// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { fakeResponse } from '@/lib/pricing-admin-test-data';
import { ExportImport } from './ExportImport';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

test('export offers the signed bundle as a download and as text', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, { bundleVersion: 1, entries: [] }));
  render(<ExportImport />);

  fireEvent.click(screen.getByRole('button', { name: 'Export versions' }));

  const link = await screen.findByRole('link', { name: 'Download bundle' });
  expect(link).toHaveAttribute('download', 'pricing-versions.json');
  expect(decodeURIComponent(String(link.getAttribute('href')))).toContain('"bundleVersion": 1');
  expect(screen.getByLabelText('Exported bundle')).toHaveAttribute('readonly');
  expect(jest.mocked(global.fetch).mock.calls[0][0]).toBe('/api/admin/pricing/versions/export');
});

test('a failed export shows the problem and no download', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(503, { code: 'PRICING_UNAVAILABLE' }));
  render(<ExportImport />);

  fireEvent.click(screen.getByRole('button', { name: 'Export versions' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('unavailable');
  expect(screen.queryByRole('link', { name: 'Download bundle' })).toBeNull();
});

test('import stays disabled until there is content and refuses invalid JSON', () => {
  global.fetch = jest.fn();
  render(<ExportImport />);
  const button = screen.getByRole('button', { name: 'Import as drafts' });
  expect(button).toBeDisabled();

  fireEvent.change(screen.getByLabelText('Bundle contents'), { target: { value: '{nope' } });
  fireEvent.click(button);

  expect(screen.getByRole('alert')).toHaveTextContent('The bundle is not valid JSON.');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('import reports created drafts and rejected entries separately', async () => {
  global.fetch = jest.fn().mockResolvedValue(
    fakeResponse(200, {
      created: [{ kind: 'RATE', subjectKey: 'thread:llm', versionId: 'v1', state: 'DRAFT' }],
      rejected: [
        { kind: 'PACKAGE', subjectKey: 'package:dma|v3|X', code: 'PRICING_BELOW_FLOOR', message: 'Floor is 25.' },
      ],
    })
  );
  render(<ExportImport />);

  fireEvent.change(screen.getByLabelText('Bundle contents'), { target: { value: '{"entries":[]}' } });
  fireEvent.click(screen.getByRole('button', { name: 'Import as drafts' }));

  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('1 drafts created, 1 entries rejected.'));
  expect(screen.getByRole('status')).toHaveTextContent('the Founder still has to authorize');
  expect(
    within(screen.getByRole('list', { name: 'Created drafts' })).getByText('RATE thread:llm: draft')
  ).toBeInTheDocument();
  expect(
    within(screen.getByRole('list', { name: 'Rejected entries' })).getByText(/below the cost floor\. Floor is 25\./)
  ).toBeInTheDocument();
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body))).toEqual({
    schemaVersion: '1.0',
    bundle: { entries: [] },
  });
});

test('an import where everything is rejected is an error', async () => {
  global.fetch = jest.fn().mockResolvedValue(
    fakeResponse(200, {
      created: [],
      rejected: [{ kind: 'RATE', subjectKey: 'thread:x', code: 'PRICING_DRAFT_INVALID', message: 'Bad.' }],
    })
  );
  render(<ExportImport />);

  fireEvent.change(screen.getByLabelText('Bundle contents'), { target: { value: '{}' } });
  fireEvent.click(screen.getByRole('button', { name: 'Import as drafts' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('0 drafts created, 1 entries rejected.');
  expect(screen.queryByRole('list', { name: 'Created drafts' })).toBeNull();
});

test('a failed import call shows the owner problem', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(403, { code: 'PRICING_FORBIDDEN' }));
  render(<ExportImport />);

  fireEvent.change(screen.getByLabelText('Bundle contents'), { target: { value: '{}' } });
  fireEvent.click(screen.getByRole('button', { name: 'Import as drafts' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Your role may not do this.');
});

test('a chosen file fills the contents', async () => {
  render(<ExportImport />);
  const file = { text: async () => '{"a":1}' } as unknown as File;

  fireEvent.change(screen.getByLabelText('Bundle file'), { target: { files: [file] } });

  await waitFor(() => expect(screen.getByLabelText('Bundle contents')).toHaveValue('{"a":1}'));
  fireEvent.change(screen.getByLabelText('Bundle file'), { target: { files: [] } });
  expect(screen.getByLabelText('Bundle contents')).toHaveValue('{"a":1}');
});
