# SubscriptionTier

## Properties

| Name                   | Type    |
| ---------------------- | ------- |
| `id`                   | string  |
| `professionalType`     | string  |
| `tierId`               | string  |
| `displayName`          | string  |
| `monthlyPriceInrPaise` | number  |
| `baseAmountPaise`      | number  |
| `gstAmountPaise`       | number  |
| `gstSacCode`           | string  |
| `isActive`             | boolean |
| `sortOrder`            | number  |

## Example

```typescript
import type { SubscriptionTier } from "";

// TODO: Update the object below with actual values
const example = {
  id: null,
  professionalType: null,
  tierId: null,
  displayName: null,
  monthlyPriceInrPaise: null,
  baseAmountPaise: null,
  gstAmountPaise: null,
  gstSacCode: null,
  isActive: null,
  sortOrder: null,
} satisfies SubscriptionTier;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SubscriptionTier;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
