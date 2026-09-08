# GenerateWhatsappUpiAutopayLink200Response

## Properties

| Name              | Type   |
| ----------------- | ------ |
| `mandateLink`     | string |
| `mandateId`       | string |
| `amountInr`       | number |
| `expiresAt`       | Date   |
| `whatsappMessage` | string |

## Example

```typescript
import type { GenerateWhatsappUpiAutopayLink200Response } from "";

// TODO: Update the object below with actual values
const example = {
  mandateLink: null,
  mandateId: null,
  amountInr: null,
  expiresAt: null,
  whatsappMessage: null,
} satisfies GenerateWhatsappUpiAutopayLink200Response;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as GenerateWhatsappUpiAutopayLink200Response;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
