import { fireEvent, render, screen } from '@testing-library/react';
import { OnboardForm } from '@/components/relationships/OnboardForm';
import { AlertFeed, type PortalAlert } from './AlertFeed';
import { ProfileEditor } from './ProfileEditor';
import { SettingsEditor } from './SettingsEditor';

const alert: PortalAlert = {
  alertId: 'alert-1', version: '1', alertType: 'ACTIONABLE', severity: 'HIGH', source: 'RELATIONSHIP_ATTENTION',
  occurredAt: '2026-08-12T09:30:00Z', dueMeaning: 'Review the decision.', readState: 'UNREAD', availableAction: 'ACKNOWLEDGE', href: '/relationships/relationship-1',
};

describe('WC084 portal editors', () => {
  afterEach(() => jest.restoreAllMocks());

  it('updates an alert from the canonical mutation response', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ version: '2', readState: 'ACKNOWLEDGED', availableAction: 'NONE' }) });
    render(<AlertFeed initialAlerts={[alert]} locale="en-IN" />);
    fireEvent.click(screen.getByRole('button', { name: 'Acknowledge' }));
    expect(await screen.findByText('acknowledged')).toBeVisible();
    expect(global.fetch).toHaveBeenCalledWith('/api/alerts/alert-1', expect.objectContaining({ method: 'POST' }));
  });

  it('keeps an alert actionable when the mutation fails', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, json: async () => ({ title: 'Version conflict' }) });
    render(<AlertFeed initialAlerts={[alert]} locale="en-IN" />);
    fireEvent.click(screen.getByRole('button', { name: 'Mark read' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Version conflict');
    expect(screen.getByRole('button', { name: 'Acknowledge' })).toBeEnabled();
  });

  it('persists profile fields through the same-origin boundary', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(<ProfileEditor displayName="Asha" organizationDisplayName="Acme" />);
    fireEvent.change(screen.getByLabelText('Display name'), { target: { value: 'Asha Rao' } });
    fireEvent.submit(screen.getByRole('button', { name: 'Save profile' }).closest('form')!);
    expect(await screen.findByText('Profile saved.')).toBeVisible();
    expect(global.fetch).toHaveBeenCalledWith('/api/identity/profile', expect.objectContaining({ method: 'PUT', body: expect.stringContaining('Asha Rao') }));
  });

  it('reports profile persistence failure', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false });
    render(<ProfileEditor displayName="Asha" organizationDisplayName="Acme" />);
    fireEvent.submit(screen.getByRole('button', { name: 'Save profile' }).closest('form')!);
    expect(await screen.findByText('Profile could not be saved.')).toBeVisible();
  });

  it('persists settings before updating presentation cookies', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(<SettingsEditor locale="en-IN" notificationPreferences={{ approvalRequests: ['WEB'], maturityReports: ['EMAIL'], monthlyNarratives: ['EMAIL'], selfGovernanceAlerts: ['WEB'] }} theme="SYSTEM" timestampVisibility="RELATIVE" />);
    fireEvent.change(screen.getByLabelText('Theme'), { target: { value: 'DARK' } });
    fireEvent.submit(screen.getByRole('button', { name: 'Save settings' }).closest('form')!);
    expect(await screen.findByText('Settings saved.')).toBeVisible();
    expect(document.cookie).toContain('waooaw-theme=dark');
  });

  it('does not update presentation cookies after a failed settings save', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false });
    render(<SettingsEditor locale="ur" notificationPreferences={{ approvalRequests: ['WEB'], maturityReports: ['EMAIL'], monthlyNarratives: ['EMAIL'], selfGovernanceAlerts: ['WEB'] }} theme="LIGHT" timestampVisibility="ABSOLUTE" />);
    fireEvent.submit(screen.getByRole('button', { name: 'Save settings' }).closest('form')!);
    expect(await screen.findByText('Settings could not be saved.')).toBeVisible();
    expect(document.cookie).not.toContain('waooaw-theme=light');
  });

  it('persists only the lightweight Onboard preferences', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true });
    render(<OnboardForm relationshipId="relationship-1" />);
    fireEvent.change(screen.getByLabelText('Agent display name'), { target: { value: 'Mira' } });
    fireEvent.submit(screen.getByRole('button', { name: 'Save Onboard preferences' }).closest('form')!);
    expect(await screen.findByText('Onboard preferences saved.')).toBeVisible();
    expect(global.fetch).toHaveBeenCalledWith('/api/relationships/relationship-1/onboard', expect.objectContaining({ method: 'PUT', body: expect.stringContaining('Mira') }));
  });

  it('reports an Onboard persistence failure', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false });
    render(<OnboardForm relationshipId="relationship-1" />);
    fireEvent.submit(screen.getByRole('button', { name: 'Save Onboard preferences' }).closest('form')!);
    expect(await screen.findByText('Onboard preferences could not be saved.')).toBeVisible();
  });
});