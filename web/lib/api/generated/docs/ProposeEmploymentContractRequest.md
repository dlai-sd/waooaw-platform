# ProposeEmploymentContractRequest

## Properties

| Name              | Type                                                                      |
| ----------------- | ------------------------------------------------------------------------- |
| `commercialTerms` | [EmploymentContractCommercialTerms](EmploymentContractCommercialTerms.md) |
| `correlationId`   | string                                                                    |

## Example

```typescript
import type { ProposeEmploymentContractRequest } from "";

// TODO: Update the object below with actual values
const example = {
  commercialTerms: null,
  correlationId: null,
} satisfies ProposeEmploymentContractRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as ProposeEmploymentContractRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
