# RelationshipUsageBudgetV1

## Properties

| Name                   | Type                                                                             |
| ---------------------- | -------------------------------------------------------------------------------- |
| `sectionType`          | [RelationshipWorkspaceSectionType](RelationshipWorkspaceSectionType.md)          |
| `currencyState`        | [RelationshipWorkspaceCurrencyState](RelationshipWorkspaceCurrencyState.md)      |
| `provenance`           | [RelationshipWorkspaceProvenanceV1](RelationshipWorkspaceProvenanceV1.md)        |
| `availableCommands`    | [Array&lt;RelationshipAvailableCommandV1&gt;](RelationshipAvailableCommandV1.md) |
| `actualAmount`         | string                                                                           |
| `forecastRange`        | string                                                                           |
| `thresholdState`       | string                                                                           |
| `wbeProjectionVersion` | string                                                                           |

## Example

```typescript
import type { RelationshipUsageBudgetV1 } from "";

// TODO: Update the object below with actual values
const example = {
  sectionType: null,
  currencyState: null,
  provenance: null,
  availableCommands: null,
  actualAmount: null,
  forecastRange: null,
  thresholdState: null,
  wbeProjectionVersion: null,
} satisfies RelationshipUsageBudgetV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipUsageBudgetV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
