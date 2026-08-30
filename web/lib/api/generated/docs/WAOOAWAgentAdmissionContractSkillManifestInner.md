# WAOOAWAgentAdmissionContractSkillManifestInner

## Properties

| Name                    | Type                                                                                                                                                |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `skillId`               | string                                                                                                                                              |
| `skillVersion`          | string                                                                                                                                              |
| `capability`            | string                                                                                                                                              |
| `businessKpi`           | string                                                                                                                                              |
| `inputs`                | Set&lt;string&gt;                                                                                                                                   |
| `outputs`               | Set&lt;string&gt;                                                                                                                                   |
| `decisionSpaceSubset`   | Set&lt;string&gt;                                                                                                                                   |
| `tools`                 | [Array&lt;WAOOAWAgentAdmissionContractSkillManifestInnerToolsInner&gt;](WAOOAWAgentAdmissionContractSkillManifestInnerToolsInner.md)                |
| `constitutionalActions` | Set&lt;string&gt;                                                                                                                                   |
| `configurationSchema`   | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |
| `goalSchema`            | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |
| `schedulePolicy`        | [WAOOAWAgentAdmissionContractSkillManifestInnerSchedulePolicy](WAOOAWAgentAdmissionContractSkillManifestInnerSchedulePolicy.md)                     |
| `reviewPolicy`          | [WAOOAWAgentAdmissionContractSkillManifestInnerReviewPolicy](WAOOAWAgentAdmissionContractSkillManifestInnerReviewPolicy.md)                         |
| `costUnits`             | { [key: string]: number; }                                                                                                                          |
| `trialBehavior`         | string                                                                                                                                              |
| `degradationBehavior`   | string                                                                                                                                              |
| `compatibility`         | [WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract](WAOOAWAgentAdmissionContractComplianceDeclarationPlatformAgentContract.md) |
| `nonGoalExemption`      | [WAOOAWAgentAdmissionContractSkillManifestInnerNonGoalExemption](WAOOAWAgentAdmissionContractSkillManifestInnerNonGoalExemption.md)                 |

## Example

```typescript
import type { WAOOAWAgentAdmissionContractSkillManifestInner } from "";

// TODO: Update the object below with actual values
const example = {
  skillId: null,
  skillVersion: null,
  capability: null,
  businessKpi: null,
  inputs: null,
  outputs: null,
  decisionSpaceSubset: null,
  tools: null,
  constitutionalActions: null,
  configurationSchema: null,
  goalSchema: null,
  schedulePolicy: null,
  reviewPolicy: null,
  costUnits: null,
  trialBehavior: null,
  degradationBehavior: null,
  compatibility: null,
  nonGoalExemption: null,
} satisfies WAOOAWAgentAdmissionContractSkillManifestInner;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as WAOOAWAgentAdmissionContractSkillManifestInner;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
