# ConversationMessageV1

## Properties

| Name               | Type                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| `schemaVersion`    | [ConversationSchemaVersion](ConversationSchemaVersion.md)                |
| `messageId`        | string                                                                   |
| `relationshipId`   | string                                                                   |
| `sequence`         | number                                                                   |
| `actor`            | [ConversationActorType](ConversationActorType.md)                        |
| `channel`          | [ConversationChannel](ConversationChannel.md)                            |
| `content`          | [Array&lt;ConversationTextBlockV1&gt;](ConversationTextBlockV1.md)       |
| `cards`            | [Array&lt;GovernedConversationCardV1&gt;](GovernedConversationCardV1.md) |
| `deliveryState`    | [ConversationDeliveryState](ConversationDeliveryState.md)                |
| `processingState`  | [ConversationProcessingState](ConversationProcessingState.md)            |
| `evidenceState`    | [ConversationEvidenceState](ConversationEvidenceState.md)                |
| `evidenceRecordId` | string                                                                   |
| `partial`          | boolean                                                                  |
| `completionReason` | [ConversationCompletionReason](ConversationCompletionReason.md)          |
| `retryOfMessageId` | string                                                                   |
| `clientMessageId`  | string                                                                   |
| `acceptedAt`       | Date                                                                     |
| `completedAt`      | Date                                                                     |

## Example

```typescript
import type { ConversationMessageV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  messageId: null,
  relationshipId: null,
  sequence: null,
  actor: null,
  channel: null,
  content: null,
  cards: null,
  deliveryState: null,
  processingState: null,
  evidenceState: null,
  evidenceRecordId: null,
  partial: null,
  completionReason: null,
  retryOfMessageId: null,
  clientMessageId: null,
  acceptedAt: null,
  completedAt: null,
} satisfies ConversationMessageV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ConversationMessageV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
