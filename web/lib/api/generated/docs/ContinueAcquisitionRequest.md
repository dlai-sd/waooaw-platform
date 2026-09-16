# ContinueAcquisitionRequest

## Properties

| Name                  | Type   |
| --------------------- | ------ |
| `professionalType`    | string |
| `professionalVersion` | string |
| `intent`              | string |
| `disclosureRevision`  | string |
| `termsVersion`        | Date   |
| `acceptance`          | string |

## Example

```typescript
import type { ContinueAcquisitionRequest } from "";

// TODO: Update the object below with actual values
const example = {
  professionalType: null,
  professionalVersion: null,
  intent: null,
  disclosureRevision: null,
  termsVersion: null,
  acceptance: null,
} satisfies ContinueAcquisitionRequest;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ContinueAcquisitionRequest;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
