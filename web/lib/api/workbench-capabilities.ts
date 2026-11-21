// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-04
// Constitutional basis: C-001, C-059, ADR-051

// The web client renders every block type of the v1 contract except DOMAIN, which therefore arrives as its fallback.
export const workbenchExperienceCapabilities =
  'channel=WEB;modality=text;blocks=TEXT:1,CHOICES:1,LIST:1,LINK:1,STATUS:1,METRIC:1,PLAN:1,DECISION:1,FORM:1,EVIDENCE:1';
