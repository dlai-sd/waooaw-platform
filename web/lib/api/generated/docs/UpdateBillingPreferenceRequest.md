# UpdateBillingPreferenceRequest

## Properties

| Name                       | Type   |
| -------------------------- | ------ |
| `billingPreference`        | string |
| `combinedBillingAnchorDay` | number |

## Example

```typescript
import type { UpdateBillingPreferenceRequest } from "";

// TODO: Update the object below with actual values
const example = {
  billingPreference: null,
  combinedBillingAnchorDay: null,
} satisfies UpdateBillingPreferenceRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as UpdateBillingPreferenceRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
