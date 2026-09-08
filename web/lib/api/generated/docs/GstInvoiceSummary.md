# GstInvoiceSummary

## Properties

| Name                   | Type                                                          |
| ---------------------- | ------------------------------------------------------------- |
| `id`                   | string                                                        |
| `employmentContractId` | string                                                        |
| `invoiceNumber`        | string                                                        |
| `invoiceDate`          | Date                                                          |
| `customerName`         | string                                                        |
| `customerGstin`        | string                                                        |
| `taxableAmountPaise`   | number                                                        |
| `cgstAmountPaise`      | number                                                        |
| `sgstAmountPaise`      | number                                                        |
| `igstAmountPaise`      | number                                                        |
| `totalAmountPaise`     | number                                                        |
| `billingPeriodStart`   | Date                                                          |
| `billingPeriodEnd`     | Date                                                          |
| `bundle`               | [DigitalMarketingPhaseBundle](DigitalMarketingPhaseBundle.md) |
| `pdfUrl`               | string                                                        |
| `consolidationGroupId` | string                                                        |
| `isConsolidatedParent` | boolean                                                       |
| `parentInvoiceId`      | string                                                        |
| `cancelledAt`          | Date                                                          |
| `createdAt`            | Date                                                          |

## Example

```typescript
import type { GstInvoiceSummary } from "";

// TODO: Update the object below with actual values
const example = {
  id: null,
  employmentContractId: null,
  invoiceNumber: null,
  invoiceDate: null,
  customerName: null,
  customerGstin: null,
  taxableAmountPaise: null,
  cgstAmountPaise: null,
  sgstAmountPaise: null,
  igstAmountPaise: null,
  totalAmountPaise: null,
  billingPeriodStart: null,
  billingPeriodEnd: null,
  bundle: null,
  pdfUrl: null,
  consolidationGroupId: null,
  isConsolidatedParent: null,
  parentInvoiceId: null,
  cancelledAt: null,
  createdAt: null,
} satisfies GstInvoiceSummary;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GstInvoiceSummary;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
