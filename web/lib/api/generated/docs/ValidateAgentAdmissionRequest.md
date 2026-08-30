# ValidateAgentAdmissionRequest

## Properties

| Name                     | Type   |
| ------------------------ | ------ |
| `revision`               | number |
| `admissionContentDigest` | string |
| `validatorProfile`       | any    |

## Example

```typescript
import type { ValidateAgentAdmissionRequest } from "";

// TODO: Update the object below with actual values
const example = {
  revision: null,
  admissionContentDigest: null,
  validatorProfile: null,
} satisfies ValidateAgentAdmissionRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ValidateAgentAdmissionRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
