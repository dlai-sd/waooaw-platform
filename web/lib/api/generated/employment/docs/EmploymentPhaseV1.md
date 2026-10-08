
# EmploymentPhaseV1


## Properties

Name | Type
------------ | -------------
`phase` | [EmploymentPhaseKind](EmploymentPhaseKind.md)
`status` | string
`progress` | [RequirementProgressV1](RequirementProgressV1.md)
`currentGoalRef` | string
`currentPlanVersion` | string
`completedItems` | [Array&lt;EmploymentWorkspaceItemV1&gt;](EmploymentWorkspaceItemV1.md)
`inProgressItems` | [Array&lt;EmploymentWorkspaceItemV1&gt;](EmploymentWorkspaceItemV1.md)
`pendingItems` | [Array&lt;EmploymentWorkspaceItemV1&gt;](EmploymentWorkspaceItemV1.md)
`blockers` | [Array&lt;EmploymentWorkspaceItemV1&gt;](EmploymentWorkspaceItemV1.md)
`assumptions` | Array&lt;string&gt;
`dependencies` | [Array&lt;EmploymentWorkspaceItemV1&gt;](EmploymentWorkspaceItemV1.md)
`milestones` | [Array&lt;EmploymentWorkspaceItemV1&gt;](EmploymentWorkspaceItemV1.md)
`calendarCommitments` | [Array&lt;CalendarCommitmentV1&gt;](CalendarCommitmentV1.md)
`billingSummary` | [EmploymentPhaseOwnerSummaryV1](EmploymentPhaseOwnerSummaryV1.md)
`performanceSummary` | [EmploymentPhaseOwnerSummaryV1](EmploymentPhaseOwnerSummaryV1.md)
`evidenceState` | [SourceState](SourceState.md)
`sourceFreshness` | Date
`limitations` | Array&lt;string&gt;
`recommendedNextAction` | string
`availableCommands` | [Array&lt;AvailableCommandV1&gt;](AvailableCommandV1.md)
`sources` | [Array&lt;EmploymentSourceV1&gt;](EmploymentSourceV1.md)

## Example

```typescript
import type { EmploymentPhaseV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "phase": null,
  "status": null,
  "progress": null,
  "currentGoalRef": null,
  "currentPlanVersion": null,
  "completedItems": null,
  "inProgressItems": null,
  "pendingItems": null,
  "blockers": null,
  "assumptions": null,
  "dependencies": null,
  "milestones": null,
  "calendarCommitments": null,
  "billingSummary": null,
  "performanceSummary": null,
  "evidenceState": null,
  "sourceFreshness": null,
  "limitations": null,
  "recommendedNextAction": null,
  "availableCommands": null,
  "sources": null,
} satisfies EmploymentPhaseV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentPhaseV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


