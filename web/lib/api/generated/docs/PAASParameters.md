# PAASParameters

Configuration for PAAS execution model

## Properties

| Name                   | Type   |
| ---------------------- | ------ |
| `sessionWindowStart`   | string |
| `sessionWindowEnd`     | string |
| `maxActionsPerSession` | number |

## Example

```typescript
import type { PAASParameters } from "";

// TODO: Update the object below with actual values
const example = {
  sessionWindowStart: null,
  sessionWindowEnd: null,
  maxActionsPerSession: null,
} satisfies PAASParameters;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PAASParameters;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
