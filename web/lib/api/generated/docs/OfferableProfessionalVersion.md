# OfferableProfessionalVersion

## Properties

| Name                     | Type                                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------------- |
| `professionalTypeId`     | string                                                                                             |
| `professionalVersion`    | string                                                                                             |
| `admissionContentDigest` | string                                                                                             |
| `displayName`            | string                                                                                             |
| `supportedChannels`      | Array&lt;string&gt;                                                                                |
| `skills`                 | [Array&lt;OfferableProfessionalVersionSkillsInner&gt;](OfferableProfessionalVersionSkillsInner.md) |

## Example

```typescript
import type { OfferableProfessionalVersion } from "";

// TODO: Update the object below with actual values
const example = {
  professionalTypeId: null,
  professionalVersion: null,
  admissionContentDigest: null,
  displayName: null,
  supportedChannels: null,
  skills: null,
} satisfies OfferableProfessionalVersion;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as OfferableProfessionalVersion;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
