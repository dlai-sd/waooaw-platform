# AdmitEmploymentRelationship201Response

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
| `schemaVersion`           | string                                                        |
| `conversationId`          | string                                                        |
| `lifecycleState`          | string                                                        |
| `engagementIntent`        | string                                                        |
| `replayed`                | boolean                                                       |
| `admittedAt`              | Date                                                          |
| `evidenceRef`             | string                                                        |
| `resumeFocus`             | [WorkspaceFocusRefV1](WorkspaceFocusRefV1.md)                 |

## Example

```typescript
import type { AdmitEmploymentRelationship201Response } from "";

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
  schemaVersion: null,
  conversationId: null,
  lifecycleState: null,
  engagementIntent: null,
  replayed: null,
  admittedAt: null,
  evidenceRef: null,
  resumeFocus: null,
} satisfies AdmitEmploymentRelationship201Response;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as AdmitEmploymentRelationship201Response;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
