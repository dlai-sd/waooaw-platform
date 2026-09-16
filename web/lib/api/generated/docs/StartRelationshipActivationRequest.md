# StartRelationshipActivationRequest

## Properties

| Name                         | Type   |
| ---------------------------- | ------ |
| `commercialOutcomeKind`      | string |
| `commercialOutcomeReference` | string |
| `commercialEvidenceId`       | string |

## Example

```typescript
import type { StartRelationshipActivationRequest } from "";

// TODO: Update the object below with actual values
const example = {
  commercialOutcomeKind: null,
  commercialOutcomeReference: null,
  commercialEvidenceId: null,
} satisfies StartRelationshipActivationRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as StartRelationshipActivationRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
