# TransitionEmploymentRelationshipRequest

Internal service command after BP authenticates the participant and resolves tenant, relationship, role, and current state. When explicitEmergencyRelease is true, BP accepts the command only from the Tier-4 portal for an active same-tenant EMPLOYER with authentication no older than five minutes. It validates the originating Stop evidence and correlation, records release evidence referencing that Stop, and only then permits a legal transition out of STOPPED_EMERGENCY. Omission, mismatch, uncertainty, or CE unavailability leaves the relationship stopped.

## Properties

| Name                           | Type                                                          |
| ------------------------------ | ------------------------------------------------------------- |
| `targetState`                  | [EmploymentRelationshipState](EmploymentRelationshipState.md) |
| `actorParticipantId`           | string                                                        |
| `actorRole`                    | [RelationshipParticipantRole](RelationshipParticipantRole.md) |
| `correlationId`                | string                                                        |
| `explicitEmergencyRelease`     | boolean                                                       |
| `originatingStopEvidenceId`    | string                                                        |
| `originatingStopCorrelationId` | string                                                        |
| `releaseConfirmation`          | string                                                        |
| `releaseJustification`         | string                                                        |

## Example

```typescript
import type { TransitionEmploymentRelationshipRequest } from "";

// TODO: Update the object below with actual values
const example = {
  targetState: null,
  actorParticipantId: null,
  actorRole: null,
  correlationId: null,
  explicitEmergencyRelease: null,
  originatingStopEvidenceId: null,
  originatingStopCorrelationId: null,
  releaseConfirmation: null,
  releaseJustification: null,
} satisfies TransitionEmploymentRelationshipRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as TransitionEmploymentRelationshipRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
