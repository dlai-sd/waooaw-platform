# AdmitEmploymentRelationshipRequest

## Properties

| Name                 | Type   |
| -------------------- | ------ |
| `evaluationIntentId` | string |
| `professionalType`   | string |
| `correlationId`      | string |

## Example

```typescript
import type { AdmitEmploymentRelationshipRequest } from "";

// TODO: Update the object below with actual values
const example = {
  evaluationIntentId: null,
  professionalType: null,
  correlationId: null,
} satisfies AdmitEmploymentRelationshipRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as AdmitEmploymentRelationshipRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
