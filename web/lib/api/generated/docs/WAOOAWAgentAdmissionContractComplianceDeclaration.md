# WAOOAWAgentAdmissionContractComplianceDeclaration

## Properties

| Name                             | Type                                                                                                                                                |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `constitutionalDna`              | [WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification](WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification.md)         |
| `agentBaseSpec`                  | [WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification](WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification.md)         |
| `platformAgentContract`          | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |
| `decisionSpaceSchema`            | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |
| `decisionConsequenceMap`         | [WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification](WAOOAWAgentAdmissionContractProfessionalIdentityAgentSpecification.md)         |
| `evidenceFirstOperations`        | Set&lt;string&gt;                                                                                                                                   |
| `emergencyStop`                  | [WAOOAWAgentAdmissionContractComplianceDeclarationEmergencyStop](WAOOAWAgentAdmissionContractComplianceDeclarationEmergencyStop.md)                 |
| `constitutionalConformanceTests` | Set&lt;string&gt;                                                                                                                                   |
| `dataClasses`                    | Set&lt;string&gt;                                                                                                                                   |
| `retentionPolicy`                | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |
| `securityPosture`                | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |
| `limitationBehavior`             | string                                                                                                                                              |
| `degradationBehavior`            | string                                                                                                                                              |

## Example

```typescript
import type { WAOOAWAgentAdmissionContractComplianceDeclaration } from "";

// TODO: Update the object below with actual values
const example = {
  constitutionalDna: null,
  agentBaseSpec: null,
  platformAgentContract: null,
  decisionSpaceSchema: null,
  decisionConsequenceMap: null,
  evidenceFirstOperations: null,
  emergencyStop: null,
  constitutionalConformanceTests: null,
  dataClasses: null,
  retentionPolicy: null,
  securityPosture: null,
  limitationBehavior: null,
  degradationBehavior: null,
} satisfies WAOOAWAgentAdmissionContractComplianceDeclaration;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as WAOOAWAgentAdmissionContractComplianceDeclaration;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
