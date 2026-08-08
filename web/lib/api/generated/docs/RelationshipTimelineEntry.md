# RelationshipTimelineEntry

## Properties

| Name                 | Type                                                          |
| -------------------- | ------------------------------------------------------------- |
| `stateVersion`       | number                                                        |
| `fromState`          | [EmploymentRelationshipState](EmploymentRelationshipState.md) |
| `toState`            | [EmploymentRelationshipState](EmploymentRelationshipState.md) |
| `actorParticipantId` | string                                                        |
| `actorRole`          | [RelationshipParticipantRole](RelationshipParticipantRole.md) |
| `correlationId`      | string                                                        |
| `evidenceId`         | string                                                        |
| `occurredAt`         | Date                                                          |

## Example

```typescript
import type { RelationshipTimelineEntry } from "";

// TODO: Update the object below with actual values
const example = {
  stateVersion: null,
  fromState: null,
  toState: null,
  actorParticipantId: null,
  actorRole: null,
  correlationId: null,
  evidenceId: null,
  occurredAt: null,
} satisfies RelationshipTimelineEntry;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipTimelineEntry;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
