# PutAgentAdmissionRevisionRequest

## Properties

| Name                     | Type                                                            |
| ------------------------ | --------------------------------------------------------------- |
| `expectedStateVersion`   | number                                                          |
| `admissionContentDigest` | string                                                          |
| `admissionContent`       | [WAOOAWAgentAdmissionContract](WAOOAWAgentAdmissionContract.md) |

## Example

```typescript
import type { PutAgentAdmissionRevisionRequest } from "";

// TODO: Update the object below with actual values
const example = {
  expectedStateVersion: null,
  admissionContentDigest: null,
  admissionContent: null,
} satisfies PutAgentAdmissionRevisionRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as PutAgentAdmissionRevisionRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
