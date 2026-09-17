# RelationshipCheckoutOutcome

## Properties

| Name                         | Type              |
| ---------------------------- | ----------------- |
| `outcomeKind`                | string            |
| `checkoutIntentId`           | string            |
| `relationshipId`             | string            |
| `contractVersion`            | number            |
| `producedAt`                 | Date              |
| `checkoutSessionId`          | string            |
| `providerOrderReference`     | string            |
| `publicCheckoutKey`          | string            |
| `amountInrPaise`             | number            |
| `currency`                   | string            |
| `merchantDisplayName`        | string            |
| `enabledMethodFamilies`      | Set&lt;string&gt; |
| `expiresAt`                  | Date              |
| `reconciliationTarget`       | string            |
| `commercialOutcomeReference` | string            |
| `commercialEvidenceId`       | string            |
| `evidenceState`              | string            |
| `quoteVersion`               | string            |
| `promotionVersion`           | string            |
| `listPriceInrPaise`          | number            |
| `discountInrPaise`           | number            |
| `taxInrPaise`                | number            |
| `payableInrPaise`            | number            |
| `renewalConsequence`         | string            |
| `reasonCode`                 | string            |
| `accountableOwner`           | string            |
| `retryable`                  | boolean           |
| `customerSafeNextAction`     | string            |

## Example

```typescript
import type { RelationshipCheckoutOutcome } from "";

// TODO: Update the object below with actual values
const example = {
  outcomeKind: null,
  checkoutIntentId: null,
  relationshipId: null,
  contractVersion: null,
  producedAt: null,
  checkoutSessionId: null,
  providerOrderReference: null,
  publicCheckoutKey: null,
  amountInrPaise: null,
  currency: null,
  merchantDisplayName: null,
  enabledMethodFamilies: null,
  expiresAt: null,
  reconciliationTarget: null,
  commercialOutcomeReference: null,
  commercialEvidenceId: null,
  evidenceState: null,
  quoteVersion: null,
  promotionVersion: null,
  listPriceInrPaise: null,
  discountInrPaise: null,
  taxInrPaise: null,
  payableInrPaise: null,
  renewalConsequence: null,
  reasonCode: null,
  accountableOwner: null,
  retryable: null,
  customerSafeNextAction: null,
} satisfies RelationshipCheckoutOutcome;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RelationshipCheckoutOutcome;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
