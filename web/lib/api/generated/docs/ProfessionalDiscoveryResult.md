# ProfessionalDiscoveryResult

## Properties

| Name                | Type                                                  |
| ------------------- | ----------------------------------------------------- |
| `professionalType`  | string                                                |
| `projectionVersion` | string                                                |
| `displayName`       | string                                                |
| `suitability`       | Array&lt;string&gt;                                   |
| `eligibility`       | [ProfessionalEligibility](ProfessionalEligibility.md) |

## Example

```typescript
import type { ProfessionalDiscoveryResult } from "";

// TODO: Update the object below with actual values
const example = {
  professionalType: null,
  projectionVersion: null,
  displayName: null,
  suitability: null,
  eligibility: null,
} satisfies ProfessionalDiscoveryResult;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProfessionalDiscoveryResult;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
