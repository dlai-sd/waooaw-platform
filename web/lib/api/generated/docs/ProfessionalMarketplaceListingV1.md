# ProfessionalMarketplaceListingV1

## Properties

| Name                 | Type                                                          |
| -------------------- | ------------------------------------------------------------- |
| `professionalType`   | string                                                        |
| `version`            | string                                                        |
| `displayName`        | string                                                        |
| `disclosurePath`     | string                                                        |
| `availableIntents`   | Set&lt;string&gt;                                             |
| `disclosureRevision` | string                                                        |
| `termsVersion`       | string                                                        |
| `suitability`        | Array&lt;string&gt;                                           |
| `capabilitySignals`  | Array&lt;string&gt;                                           |
| `limitations`        | Array&lt;string&gt;                                           |
| `customerRights`     | Array&lt;string&gt;                                           |
| `eligibility`        | [ProfessionalEligibility](ProfessionalEligibility.md)         |
| `indicativePrice`    | [IndicativePriceDisclosure](IndicativePriceDisclosure.md)     |
| `trial`              | [ProfessionalTrialDisclosure](ProfessionalTrialDisclosure.md) |
| `evidencePosture`    | string                                                        |
| `offerabilityState`  | string                                                        |
| `trialTerms`         | string                                                        |
| `nextAction`         | string                                                        |

## Example

```typescript
import type { ProfessionalMarketplaceListingV1 } from "";

// TODO: Update the object below with actual values
const example = {
  professionalType: null,
  version: null,
  displayName: null,
  disclosurePath: null,
  availableIntents: null,
  disclosureRevision: null,
  termsVersion: null,
  suitability: null,
  capabilitySignals: null,
  limitations: null,
  customerRights: null,
  eligibility: null,
  indicativePrice: null,
  trial: null,
  evidencePosture: null,
  offerabilityState: null,
  trialTerms: null,
  nextAction: null,
} satisfies ProfessionalMarketplaceListingV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as ProfessionalMarketplaceListingV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
