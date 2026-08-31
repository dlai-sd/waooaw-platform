# ProfessionalTrialDisclosure

## Properties

| Name                     | Type    |
| ------------------------ | ------- |
| `available`              | boolean |
| `durationDays`           | number  |
| `paidApiCallsAllowed`    | boolean |
| `externalActionsAllowed` | boolean |

## Example

```typescript
import type { ProfessionalTrialDisclosure } from "";

// TODO: Update the object below with actual values
const example = {
  available: null,
  durationDays: null,
  paidApiCallsAllowed: null,
  externalActionsAllowed: null,
} satisfies ProfessionalTrialDisclosure;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProfessionalTrialDisclosure;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
