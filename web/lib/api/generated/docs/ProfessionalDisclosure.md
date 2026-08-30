# ProfessionalDisclosure

## Properties

| Name                | Type                                                                       |
| ------------------- | -------------------------------------------------------------------------- |
| `professionalType`  | string                                                                     |
| `projectionVersion` | string                                                                     |
| `displayName`       | string                                                                     |
| `suitability`       | Array&lt;string&gt;                                                        |
| `skills`            | [Array&lt;ProfessionalSkillDisclosure&gt;](ProfessionalSkillDisclosure.md) |
| `limitations`       | Array&lt;string&gt;                                                        |
| `authorityNeeds`    | Array&lt;string&gt;                                                        |
| `customerRights`    | Array&lt;string&gt;                                                        |
| `trial`             | [ProfessionalTrialDisclosure](ProfessionalTrialDisclosure.md)              |
| `evidencePosture`   | string                                                                     |
| `indicativePrice`   | [IndicativePriceDisclosure](IndicativePriceDisclosure.md)                  |
| `eligibility`       | [ProfessionalEligibility](ProfessionalEligibility.md)                      |

## Example

```typescript
import type { ProfessionalDisclosure } from "";

// TODO: Update the object below with actual values
const example = {
  professionalType: null,
  projectionVersion: null,
  displayName: null,
  suitability: null,
  skills: null,
  limitations: null,
  authorityNeeds: null,
  customerRights: null,
  trial: null,
  evidencePosture: null,
  indicativePrice: null,
  eligibility: null,
} satisfies ProfessionalDisclosure;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProfessionalDisclosure;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
