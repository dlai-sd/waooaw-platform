# RelationshipRightsControlsV1

## Properties

| Name                     | Type                                                                             |
| ------------------------ | -------------------------------------------------------------------------------- |
| `sectionType`            | [RelationshipWorkspaceSectionType](RelationshipWorkspaceSectionType.md)          |
| `currencyState`          | [RelationshipWorkspaceCurrencyState](RelationshipWorkspaceCurrencyState.md)      |
| `provenance`             | [RelationshipWorkspaceProvenanceV1](RelationshipWorkspaceProvenanceV1.md)        |
| `availableCommands`      | [Array&lt;RelationshipAvailableCommandV1&gt;](RelationshipAvailableCommandV1.md) |
| `scopeVersion`           | string                                                                           |
| `authorityVersion`       | string                                                                           |
| `lifecycleState`         | [EmploymentRelationshipState](EmploymentRelationshipState.md)                    |
| `emergencyStopReachable` | boolean                                                                          |

## Example

```typescript
import type { RelationshipRightsControlsV1 } from "";

// TODO: Update the object below with actual values
const example = {
  sectionType: null,
  currencyState: null,
  provenance: null,
  availableCommands: null,
  scopeVersion: null,
  authorityVersion: null,
  lifecycleState: null,
  emergencyStopReachable: null,
} satisfies RelationshipRightsControlsV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipRightsControlsV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
