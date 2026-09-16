# RelationshipFullyDiscountedCheckout

## Properties

| Name                         | Type   |
| ---------------------------- | ------ |
| `outcomeKind`                | string |
| `checkoutIntentId`           | string |
| `relationshipId`             | string |
| `contractVersion`            | number |
| `producedAt`                 | Date   |
| `quoteVersion`               | string |
| `promotionVersion`           | string |
| `listPriceInrPaise`          | number |
| `discountInrPaise`           | number |
| `taxInrPaise`                | number |
| `payableInrPaise`            | number |
| `renewalConsequence`         | string |
| `commercialOutcomeReference` | string |
| `commercialEvidenceId`       | string |
| `evidenceState`              | string |

## Example

```typescript
import type { RelationshipFullyDiscountedCheckout } from "";

// TODO: Update the object below with actual values
const example = {
  outcomeKind: null,
  checkoutIntentId: null,
  relationshipId: null,
  contractVersion: null,
  producedAt: null,
  quoteVersion: null,
  promotionVersion: null,
  listPriceInrPaise: null,
  discountInrPaise: null,
  taxInrPaise: null,
  payableInrPaise: null,
  renewalConsequence: null,
  commercialOutcomeReference: null,
  commercialEvidenceId: null,
  evidenceState: null,
} satisfies RelationshipFullyDiscountedCheckout;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipFullyDiscountedCheckout;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
