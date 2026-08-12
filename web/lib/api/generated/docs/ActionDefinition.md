# ActionDefinition

## Properties

| Name          | Type   |
| ------------- | ------ |
| `actionType`  | string |
| `description` | string |
| `parameters`  | object |

## Example

```typescript
import type { ActionDefinition } from "";

// TODO: Update the object below with actual values
const example = {
  actionType: null,
  description: null,
  parameters: null,
} satisfies ActionDefinition;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ActionDefinition;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
