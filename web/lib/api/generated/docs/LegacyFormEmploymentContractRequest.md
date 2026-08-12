# LegacyFormEmploymentContractRequest

## Properties

| Name                 | Type                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------- |
| `professionalId`     | string                                                                                                  |
| `decisionSpace`      | [LegacyFormEmploymentContractRequestDecisionSpace](LegacyFormEmploymentContractRequestDecisionSpace.md) |
| `evaluationIntentId` | string                                                                                                  |
| `correlationId`      | string                                                                                                  |

## Example

```typescript
import type { LegacyFormEmploymentContractRequest } from "";

// TODO: Update the object below with actual values
const example = {
  professionalId: null,
  decisionSpace: null,
  evaluationIntentId: null,
  correlationId: null,
} satisfies LegacyFormEmploymentContractRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as LegacyFormEmploymentContractRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
