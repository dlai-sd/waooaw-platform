# WAOOAWAgentAdmissionContractSkillManifestInnerNonGoalExemption

## Properties

| Name                                | Type              |
| ----------------------------------- | ----------------- |
| `exemptionId`                       | string            |
| `purpose`                           | string            |
| `scope`                             | string            |
| `measurableOperationalOutcome`      | string            |
| `approvingAuthority`                | string            |
| `constitutionalAcceptanceReference` | string            |
| `effectiveFrom`                     | Date              |
| `effectiveUntil`                    | Date              |
| `revocationConditions`              | Set&lt;string&gt; |

## Example

```typescript
import type { WAOOAWAgentAdmissionContractSkillManifestInnerNonGoalExemption } from "";

// TODO: Update the object below with actual values
const example = {
  exemptionId: null,
  purpose: null,
  scope: null,
  measurableOperationalOutcome: null,
  approvingAuthority: null,
  constitutionalAcceptanceReference: null,
  effectiveFrom: null,
  effectiveUntil: null,
  revocationConditions: null,
} satisfies WAOOAWAgentAdmissionContractSkillManifestInnerNonGoalExemption;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as WAOOAWAgentAdmissionContractSkillManifestInnerNonGoalExemption;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
