# RelationshipWorkspaceProblemDetailV1

RFC 9457 relationship workspace error with privacy-safe extensions

## Properties

| Name                     | Type                                                                        |
| ------------------------ | --------------------------------------------------------------------------- |
| `type`                   | string                                                                      |
| `title`                  | string                                                                      |
| `status`                 | number                                                                      |
| `detail`                 | string                                                                      |
| `code`                   | [RelationshipWorkspaceProblemCodeV1](RelationshipWorkspaceProblemCodeV1.md) |
| `correlationId`          | string                                                                      |
| `reconciliationRequired` | boolean                                                                     |
| `retryAfterSeconds`      | number                                                                      |

## Example

```typescript
import type { RelationshipWorkspaceProblemDetailV1 } from "";

// TODO: Update the object below with actual values
const example = {
  type: null,
  title: null,
  status: null,
  detail: null,
  code: null,
  correlationId: null,
  reconciliationRequired: null,
  retryAfterSeconds: null,
} satisfies RelationshipWorkspaceProblemDetailV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipWorkspaceProblemDetailV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
