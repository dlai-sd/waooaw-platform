# WAOOAWAgentAdmissionContract

Submitter-controlled immutable content for professional-version admission. Activation evidence is platform-owned and excluded.

## Properties

| Name                      | Type                                                                                                             |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `contractSchemaVersion`   | any                                                                                                              |
| `canonicalizationProfile` | any                                                                                                              |
| `professionalIdentity`    | [WAOOAWAgentAdmissionContractProfessionalIdentity](WAOOAWAgentAdmissionContractProfessionalIdentity.md)          |
| `complianceDeclaration`   | [WAOOAWAgentAdmissionContractComplianceDeclaration](WAOOAWAgentAdmissionContractComplianceDeclaration.md)        |
| `skillManifest`           | [Array&lt;WAOOAWAgentAdmissionContractSkillManifestInner&gt;](WAOOAWAgentAdmissionContractSkillManifestInner.md) |

## Example

```typescript
import type { WAOOAWAgentAdmissionContract } from "";

// TODO: Update the object below with actual values
const example = {
  contractSchemaVersion: null,
  canonicalizationProfile: null,
  professionalIdentity: null,
  complianceDeclaration: null,
  skillManifest: null,
} satisfies WAOOAWAgentAdmissionContract;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as WAOOAWAgentAdmissionContract;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
