# WAOOAWAgentAdmissionContractRuntimeAdapter

## Properties

| Name                      | Type                                                                                                                                                |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `protocolVersion`         | any                                                                                                                                                 |
| `compatibleMinorVersions` | Set&lt;string&gt;                                                                                                                                   |
| `artifactDigest`          | string                                                                                                                                              |
| `isolationProfile`        | any                                                                                                                                                 |
| `conformanceEvidence`     | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |

## Example

```typescript
import type { WAOOAWAgentAdmissionContractRuntimeAdapter } from "";

// TODO: Update the object below with actual values
const example = {
  protocolVersion: null,
  compatibleMinorVersions: null,
  artifactDigest: null,
  isolationProfile: null,
  conformanceEvidence: null,
} satisfies WAOOAWAgentAdmissionContractRuntimeAdapter;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as WAOOAWAgentAdmissionContractRuntimeAdapter;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
