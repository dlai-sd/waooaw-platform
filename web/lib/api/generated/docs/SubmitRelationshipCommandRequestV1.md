# SubmitRelationshipCommandRequestV1

## Properties

| Name                       | Type                                                                        |
| -------------------------- | --------------------------------------------------------------------------- |
| `schemaVersion`            | [RelationshipWorkspaceSchemaVersion](RelationshipWorkspaceSchemaVersion.md) |
| `expectedWorkspaceVersion` | string                                                                      |
| `expectedSubjectVersion`   | string                                                                      |
| `payload`                  | [RelationshipTypedCommandPayloadV1](RelationshipTypedCommandPayloadV1.md)   |

## Example

```typescript
import type { SubmitRelationshipCommandRequestV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  expectedWorkspaceVersion: null,
  expectedSubjectVersion: null,
  payload: null,
} satisfies SubmitRelationshipCommandRequestV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as SubmitRelationshipCommandRequestV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
