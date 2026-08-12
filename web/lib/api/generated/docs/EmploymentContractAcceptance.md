# EmploymentContractAcceptance

## Properties

| Name                      | Type   |
| ------------------------- | ------ |
| `acceptanceId`            | string |
| `contractId`              | string |
| `contractVersion`         | number |
| `contractHash`            | string |
| `authenticationAssurance` | string |
| `acceptanceEvidenceId`    | string |
| `acceptedAt`              | Date   |

## Example

```typescript
import type { EmploymentContractAcceptance } from "";

// TODO: Update the object below with actual values
const example = {
  acceptanceId: null,
  contractId: null,
  contractVersion: null,
  contractHash: null,
  authenticationAssurance: null,
  acceptanceEvidenceId: null,
  acceptedAt: null,
} satisfies EmploymentContractAcceptance;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentContractAcceptance;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
