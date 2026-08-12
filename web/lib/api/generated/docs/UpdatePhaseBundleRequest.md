# UpdatePhaseBundleRequest

## Properties

| Name                        | Type   |
| --------------------------- | ------ |
| `bundle`                    | string |
| `maturityScoreAtActivation` | number |

## Example

```typescript
import type { UpdatePhaseBundleRequest } from "";

// TODO: Update the object below with actual values
const example = {
  bundle: null,
  maturityScoreAtActivation: null,
} satisfies UpdatePhaseBundleRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as UpdatePhaseBundleRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
