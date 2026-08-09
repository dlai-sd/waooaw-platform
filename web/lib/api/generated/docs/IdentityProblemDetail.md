# IdentityProblemDetail

RFC 9457 identity error with privacy-safe extension fields

## Properties

| Name                | Type                                          |
| ------------------- | --------------------------------------------- |
| `type`              | string                                        |
| `title`             | string                                        |
| `status`            | number                                        |
| `detail`            | string                                        |
| `code`              | [IdentityProblemCode](IdentityProblemCode.md) |
| `correlationId`     | string                                        |
| `retryAfterSeconds` | number                                        |
| `stepUpIntentId`    | string                                        |

## Example

```typescript
import type { IdentityProblemDetail } from "";

// TODO: Update the object below with actual values
const example = {
  type: null,
  title: null,
  status: null,
  detail: null,
  code: null,
  correlationId: null,
  retryAfterSeconds: null,
  stepUpIntentId: null,
} satisfies IdentityProblemDetail;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityProblemDetail;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
