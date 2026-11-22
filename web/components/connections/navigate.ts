// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R008, WC149-R010
// Constitutional basis: C-026, C-059, C-063

// The browser leaves for the Facebook consent screen; isolated so tests can observe it.
export function navigateTo(url: string): void {
  window.location.assign(url);
}

export function isSafeAuthorizationUrl(value: unknown): value is string {
  return typeof value === 'string' && /^https:\/\/[^\s/]+\S*$/i.test(value);
}
