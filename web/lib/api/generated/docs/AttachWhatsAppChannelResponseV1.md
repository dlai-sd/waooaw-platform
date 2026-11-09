# AttachWhatsAppChannelResponseV1

## Properties

| Name             | Type   |
| ---------------- | ------ |
| `schemaVersion`  | string |
| `relationshipId` | string |
| `bindingId`      | string |
| `channel`        | string |
| `status`         | string |
| `assurance`      | string |

## Example

```typescript
import type { AttachWhatsAppChannelResponseV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  relationshipId: null,
  bindingId: null,
  channel: null,
  status: null,
  assurance: null,
} satisfies AttachWhatsAppChannelResponseV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as AttachWhatsAppChannelResponseV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
