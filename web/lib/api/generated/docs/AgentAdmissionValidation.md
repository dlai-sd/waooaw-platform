# AgentAdmissionValidation

## Properties

| Name           | Type   |
| -------------- | ------ |
| `validationId` | string |
| `revision`     | number |
| `profile`      | string |
| `result`       | string |
| `findingCount` | number |

## Example

```typescript
import type { AgentAdmissionValidation } from "";

// TODO: Update the object below with actual values
const example = {
  validationId: null,
  revision: null,
  profile: null,
  result: null,
  findingCount: null,
} satisfies AgentAdmissionValidation;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AgentAdmissionValidation;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
