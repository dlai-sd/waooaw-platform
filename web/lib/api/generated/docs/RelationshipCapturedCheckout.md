# RelationshipCapturedCheckout

## Properties

| Name                         | Type   |
| ---------------------------- | ------ |
| `outcomeKind`                | string |
| `checkoutIntentId`           | string |
| `relationshipId`             | string |
| `contractVersion`            | number |
| `producedAt`                 | Date   |
| `commercialOutcomeReference` | string |
| `commercialEvidenceId`       | string |
| `evidenceState`              | string |

## Example

```typescript
import type { RelationshipCapturedCheckout } from "";

// TODO: Update the object below with actual values
const example = {
  outcomeKind: null,
  checkoutIntentId: null,
  relationshipId: null,
  contractVersion: null,
  producedAt: null,
  commercialOutcomeReference: null,
  commercialEvidenceId: null,
  evidenceState: null,
} satisfies RelationshipCapturedCheckout;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipCapturedCheckout;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
