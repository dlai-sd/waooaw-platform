# PhaseBundleSubscription

## Properties

| Name                         | Type                                                          |
| ---------------------------- | ------------------------------------------------------------- |
| `id`                         | string                                                        |
| `employmentContractId`       | string                                                        |
| `bundle`                     | [DigitalMarketingPhaseBundle](DigitalMarketingPhaseBundle.md) |
| `activatedAt`                | Date                                                          |
| `deactivatedAt`              | Date                                                          |
| `maturityScoreAtActivation`  | number                                                        |
| `customerAuthorizationEvent` | string                                                        |
| `activatedBy`                | string                                                        |
| `createdAt`                  | Date                                                          |

## Example

```typescript
import type { PhaseBundleSubscription } from "";

// TODO: Update the object below with actual values
const example = {
  id: null,
  employmentContractId: null,
  bundle: null,
  activatedAt: null,
  deactivatedAt: null,
  maturityScoreAtActivation: null,
  customerAuthorizationEvent: null,
  activatedBy: null,
  createdAt: null,
} satisfies PhaseBundleSubscription;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PhaseBundleSubscription;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
