# NeutralContinuityEnvelope

Channel-neutral handoff state signed by BP with HMAC-SHA256 over RFC 8785 canonical JSON bytes. The signature covers every property except integritySignature. Only BP and authenticated internal services verify the signature with the managed continuity-envelope key; it is not a browser authorization credential. Verification failure rejects activation without mutating binding or relationship state. Tenant, relationship, participant, role, assurance, and authority fields are server-resolved and cannot be supplied or overridden by channel payloads.

## Properties

| Name                      | Type                                                                          |
| ------------------------- | ----------------------------------------------------------------------------- |
| `schemaVersion`           | string                                                                        |
| `tenantId`                | string                                                                        |
| `relationshipId`          | string                                                                        |
| `participantId`           | string                                                                        |
| `participantRole`         | [RelationshipParticipantRole](RelationshipParticipantRole.md)                 |
| `authenticationAssurance` | [RelationshipAuthenticationAssurance](RelationshipAuthenticationAssurance.md) |
| `authoritySnapshotId`     | string                                                                        |
| `sourceChannel`           | [RelationshipChannel](RelationshipChannel.md)                                 |
| `sourceConversationId`    | string                                                                        |
| `targetChannel`           | [RelationshipChannel](RelationshipChannel.md)                                 |
| `targetConversationId`    | string                                                                        |
| `commandPurpose`          | string                                                                        |
| `correlationId`           | string                                                                        |
| `causalMarker`            | string                                                                        |
| `sequenceNumber`          | number                                                                        |
| `idempotencyKey`          | string                                                                        |
| `evidenceCommitmentId`    | string                                                                        |
| `continuityCheckpointId`  | string                                                                        |
| `issuedAt`                | Date                                                                          |
| `integritySignature`      | string                                                                        |

## Example

```typescript
import type { NeutralContinuityEnvelope } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  tenantId: null,
  relationshipId: null,
  participantId: null,
  participantRole: null,
  authenticationAssurance: null,
  authoritySnapshotId: null,
  sourceChannel: null,
  sourceConversationId: null,
  targetChannel: null,
  targetConversationId: null,
  commandPurpose: null,
  correlationId: null,
  causalMarker: null,
  sequenceNumber: null,
  idempotencyKey: null,
  evidenceCommitmentId: null,
  continuityCheckpointId: null,
  issuedAt: null,
  integritySignature: null,
} satisfies NeutralContinuityEnvelope;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as NeutralContinuityEnvelope;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
