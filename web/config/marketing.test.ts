// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Destination And Environment Matrix
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { marketingConfig } from './marketing';
describe('marketing configuration', () => {
  it('fails destinations safely when identifiers are absent', () => {
    expect(marketingConfig.ga4.id).toBeUndefined();
    expect(marketingConfig.meta.id).toBeUndefined();
  });
  it('keeps every optional destination disabled by default', () => {
    expect(marketingConfig.ga4.enabled).toBe(false);
    expect(marketingConfig.serverGtm.enabled).toBe(false);
    expect(marketingConfig.meta.enabled).toBe(false);
  });
});