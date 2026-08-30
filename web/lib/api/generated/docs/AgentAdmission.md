# AgentAdmission

## Properties

| Name                     | Type                                          |
| ------------------------ | --------------------------------------------- |
| `admissionId`            | string                                        |
| `professionalTypeId`     | string                                        |
| `professionalVersion`    | string                                        |
| `state`                  | [AgentAdmissionState](AgentAdmissionState.md) |
| `stateVersion`           | number                                        |
| `currentRevision`        | number                                        |
| `admissionContentDigest` | string                                        |
| `createdAt`              | Date                                          |
| `updatedAt`              | Date                                          |

## Example

```typescript
import type { AgentAdmission } from "";

// TODO: Update the object below with actual values
const example = {
  admissionId: null,
  professionalTypeId: null,
  professionalVersion: null,
  state: null,
  stateVersion: null,
  currentRevision: null,
  admissionContentDigest: null,
  createdAt: null,
  updatedAt: null,
} satisfies AgentAdmission;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AgentAdmission;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
