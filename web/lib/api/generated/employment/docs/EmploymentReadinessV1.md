
# EmploymentReadinessV1


## Properties

Name | Type
------------ | -------------
`induction` | [InductionReadinessState](InductionReadinessState.md)
`plan` | [PlanReadinessState](PlanReadinessState.md)
`operations` | [OperationsEligibilityState](OperationsEligibilityState.md)
`performance` | [PerformanceAssuranceState](PerformanceAssuranceState.md)
`eligibleSkillRefs` | Array&lt;string&gt;
`lockedSkillRefs` | Array&lt;string&gt;
`unmetConditions` | Array&lt;string&gt;
`sources` | [Array&lt;EmploymentSourceV1&gt;](EmploymentSourceV1.md)

## Example

```typescript
import type { EmploymentReadinessV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "induction": null,
  "plan": null,
  "operations": null,
  "performance": null,
  "eligibleSkillRefs": null,
  "lockedSkillRefs": null,
  "unmetConditions": null,
  "sources": null,
} satisfies EmploymentReadinessV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentReadinessV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


