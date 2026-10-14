# ConversationChannelSessionEndOutcomeV1

## Properties

| Name                        | Type    |
| --------------------------- | ------- |
| `schemaVersion`             | string  |
| `channelSessionId`          | string  |
| `channel`                   | string  |
| `state`                     | string  |
| `sessionVersion`            | number  |
| `endedAt`                   | Date    |
| `replayed`                  | boolean |
| `relationshipRemainsActive` | boolean |
| `evidenceRef`               | string  |

## Example

```typescript
import type { ConversationChannelSessionEndOutcomeV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  channelSessionId: null,
  channel: null,
  state: null,
  sessionVersion: null,
  endedAt: null,
  replayed: null,
  relationshipRemainsActive: null,
  evidenceRef: null,
} satisfies ConversationChannelSessionEndOutcomeV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as ConversationChannelSessionEndOutcomeV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
