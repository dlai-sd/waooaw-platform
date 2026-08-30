# IndicativePriceDisclosure

## Properties

| Name             | Type   |
| ---------------- | ------ |
| `currency`       | string |
| `amountInrPaise` | number |
| `cadence`        | string |
| `qualification`  | string |

## Example

```typescript
import type { IndicativePriceDisclosure } from "";

// TODO: Update the object below with actual values
const example = {
  currency: null,
  amountInrPaise: null,
  cadence: null,
  qualification: null,
} satisfies IndicativePriceDisclosure;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as IndicativePriceDisclosure;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
