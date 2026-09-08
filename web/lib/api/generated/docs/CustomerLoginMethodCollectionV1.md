# CustomerLoginMethodCollectionV1

## Properties

| Name            | Type                                                           |
| --------------- | -------------------------------------------------------------- |
| `schemaVersion` | [CustomerPortalSchemaVersion](CustomerPortalSchemaVersion.md)  |
| `items`         | [Array&lt;CustomerLoginMethodV1&gt;](CustomerLoginMethodV1.md) |

## Example

```typescript
import type { CustomerLoginMethodCollectionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  items: null,
} satisfies CustomerLoginMethodCollectionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as CustomerLoginMethodCollectionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
