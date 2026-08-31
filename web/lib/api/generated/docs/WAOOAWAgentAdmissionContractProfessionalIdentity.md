# WAOOAWAgentAdmissionContractProfessionalIdentity

## Properties

| Name                        | Type                                                                                                                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `professionalTypeId`        | string                                                                                                                                      |
| `professionalVersion`       | string                                                                                                                                      |
| `ownerSubjectId`            | string                                                                                                                                      |
| `supportedLanguages`        | Set&lt;string&gt;                                                                                                                           |
| `supportedChannels`         | Set&lt;string&gt;                                                                                                                           |
| `agentSpecification`        | [WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification](WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification.md) |
| `agentVerificationDocument` | [WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification](WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification.md) |
| `predecessorVersion`        | string                                                                                                                                      |

## Example

```typescript
import type { WAOOAWAgentAdmissionContractProfessionalIdentity } from "";

// TODO: Update the object below with actual values
const example = {
  professionalTypeId: null,
  professionalVersion: null,
  ownerSubjectId: null,
  supportedLanguages: null,
  supportedChannels: null,
  agentSpecification: null,
  agentVerificationDocument: null,
  predecessorVersion: null,
} satisfies WAOOAWAgentAdmissionContractProfessionalIdentity;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as WAOOAWAgentAdmissionContractProfessionalIdentity;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
