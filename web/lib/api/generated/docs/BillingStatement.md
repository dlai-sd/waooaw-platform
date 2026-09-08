# BillingStatement

## Properties

| Name          | Type                                               |
| ------------- | -------------------------------------------------- |
| `tenantId`    | string                                             |
| `periodStart` | Date                                               |
| `periodEnd`   | Date                                               |
| `totalAmount` | number                                             |
| `lineItems`   | [Array&lt;BillingLineItem&gt;](BillingLineItem.md) |

## Example

```typescript
import type { BillingStatement } from "";

// TODO: Update the object below with actual values
const example = {
  tenantId: null,
  periodStart: null,
  periodEnd: null,
  totalAmount: null,
  lineItems: null,
} satisfies BillingStatement;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BillingStatement;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
