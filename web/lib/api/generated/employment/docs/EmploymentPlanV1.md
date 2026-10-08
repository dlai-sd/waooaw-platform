
# EmploymentPlanV1


## Properties

Name | Type
------------ | -------------
`planId` | string
`planVersion` | string
`priorPlanVersion` | string
`state` | [PlanState](PlanState.md)
`goalRef` | string
`outcomeLabel` | string
`accountableOwner` | string
`skillRefs` | Array&lt;string&gt;
`milestones` | [Array&lt;EmploymentWorkspaceItemV1&gt;](EmploymentWorkspaceItemV1.md)
`calendarCommitments` | [Array&lt;CalendarCommitmentV1&gt;](CalendarCommitmentV1.md)
`impactSummary` | string
`source` | [EmploymentSourceV1](EmploymentSourceV1.md)

## Example

```typescript
import type { EmploymentPlanV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "planId": null,
  "planVersion": null,
  "priorPlanVersion": null,
  "state": null,
  "goalRef": null,
  "outcomeLabel": null,
  "accountableOwner": null,
  "skillRefs": null,
  "milestones": null,
  "calendarCommitments": null,
  "impactSummary": null,
  "source": null,
} satisfies EmploymentPlanV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentPlanV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


