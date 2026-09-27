# PrepareRelationshipHireRequest

## Properties

| Name                         | Type              |
| ---------------------------- | ----------------- |
| `businessName`               | string            |
| `location`                   | string            |
| `businessNature`             | string            |
| `goal`                       | string            |
| `successMeasure`             | string            |
| `budgetCeilingInrPaise`      | number            |
| `selectedSkillIds`           | Set&lt;string&gt; |
| `authorityScopeConfirmation` | string            |
| `correlationId`              | string            |

## Example

```typescript
import type { PrepareRelationshipHireRequest } from "";

// TODO: Update the object below with actual values
const example = {
  businessName: null,
  location: null,
  businessNature: null,
  goal: null,
  successMeasure: null,
  budgetCeilingInrPaise: null,
  selectedSkillIds: null,
  authorityScopeConfirmation: null,
  correlationId: null,
} satisfies PrepareRelationshipHireRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PrepareRelationshipHireRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
