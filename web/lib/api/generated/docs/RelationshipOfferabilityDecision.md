# RelationshipOfferabilityDecision

## Properties

| Name                      | Type                       |
| ------------------------- | -------------------------- |
| `schemaVersion`           | string                     |
| `decisionId`              | string                     |
| `relationshipId`          | string                     |
| `disposition`             | string                     |
| `directContributionPaise` | number                     |
| `policyVersion`           | string                     |
| `ownerVersions`           | { [key: string]: string; } |
| `reasons`                 | Array&lt;string&gt;        |
| `evidenceId`              | string                     |
| `producedAt`              | Date                       |
| `expiresAt`               | Date                       |

## Example

```typescript
import type { RelationshipOfferabilityDecision } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  decisionId: null,
  relationshipId: null,
  disposition: null,
  directContributionPaise: null,
  policyVersion: null,
  ownerVersions: null,
  reasons: null,
  evidenceId: null,
  producedAt: null,
  expiresAt: null,
} satisfies RelationshipOfferabilityDecision;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipOfferabilityDecision;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
