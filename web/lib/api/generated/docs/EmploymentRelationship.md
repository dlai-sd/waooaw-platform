# EmploymentRelationship

## Properties

| Name                      | Type                                                          |
| ------------------------- | ------------------------------------------------------------- |
| `relationshipId`          | string                                                        |
| `agentInstanceId`         | string                                                        |
| `professionalAdmissionId` | string                                                        |
| `professionalType`        | string                                                        |
| `professionalVersion`     | string                                                        |
| `agentInstanceMintedAt`   | Date                                                          |
| `state`                   | [EmploymentRelationshipState](EmploymentRelationshipState.md) |
| `stateVersion`            | number                                                        |
| `createdAt`               | Date                                                          |
| `updatedAt`               | Date                                                          |

## Example

```typescript
import type { EmploymentRelationship } from "";

// TODO: Update the object below with actual values
const example = {
  relationshipId: null,
  agentInstanceId: null,
  professionalAdmissionId: null,
  professionalType: null,
  professionalVersion: null,
  agentInstanceMintedAt: null,
  state: null,
  stateVersion: null,
  createdAt: null,
  updatedAt: null,
} satisfies EmploymentRelationship;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentRelationship;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
