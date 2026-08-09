# IdentityCompletion

## Properties

| Name               | Type                                                |
| ------------------ | --------------------------------------------------- |
| `outcome`          | string                                              |
| `accountReference` | string                                              |
| `assuranceLevel`   | [IdentityAssuranceLevel](IdentityAssuranceLevel.md) |
| `defaultTarget`    | string                                              |

## Example

```typescript
import type { IdentityCompletion } from "";

// TODO: Update the object below with actual values
const example = {
  outcome: null,
  accountReference: null,
  assuranceLevel: null,
  defaultTarget: null,
} satisfies IdentityCompletion;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IdentityCompletion;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
