# RelationshipGoalsV1

## Properties

| Name                | Type                                                                             |
| ------------------- | -------------------------------------------------------------------------------- |
| `sectionType`       | [RelationshipWorkspaceSectionType](RelationshipWorkspaceSectionType.md)          |
| `currencyState`     | [RelationshipWorkspaceCurrencyState](RelationshipWorkspaceCurrencyState.md)      |
| `provenance`        | [RelationshipWorkspaceProvenanceV1](RelationshipWorkspaceProvenanceV1.md)        |
| `availableCommands` | [Array&lt;RelationshipAvailableCommandV1&gt;](RelationshipAvailableCommandV1.md) |
| `activeGoals`       | [Array&lt;RelationshipGoalV1&gt;](RelationshipGoalV1.md)                         |
| `history`           | [Array&lt;RelationshipGoalHistoryEntryV1&gt;](RelationshipGoalHistoryEntryV1.md) |

## Example

```typescript
import type { RelationshipGoalsV1 } from "";

// TODO: Update the object below with actual values
const example = {
  sectionType: null,
  currencyState: null,
  provenance: null,
  availableCommands: null,
  activeGoals: null,
  history: null,
} satisfies RelationshipGoalsV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipGoalsV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
