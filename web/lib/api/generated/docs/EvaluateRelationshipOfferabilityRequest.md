# EvaluateRelationshipOfferabilityRequest

## Properties

| Name                 | Type   |
| -------------------- | ------ |
| `schemaVersion`      | string |
| `offeringId`         | string |
| `agentType`          | string |
| `bundleTier`         | string |
| `proposedPricePaise` | number |

## Example

```typescript
import type { EvaluateRelationshipOfferabilityRequest } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  offeringId: null,
  agentType: null,
  bundleTier: null,
  proposedPricePaise: null,
} satisfies EvaluateRelationshipOfferabilityRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as EvaluateRelationshipOfferabilityRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
