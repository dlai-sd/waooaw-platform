
# EmploymentWorkspaceV1


## Properties

Name | Type
------------ | -------------
`schemaVersion` | [EmploymentSchemaVersion](EmploymentSchemaVersion.md)
`protocolVersion` | string
`relationshipId` | string
`workspaceVersion` | string
`agentType` | string
`agentVersion` | string
`manifestVersion` | string
`readiness` | [EmploymentReadinessV1](EmploymentReadinessV1.md)
`phases` | [Array&lt;EmploymentPhaseV1&gt;](EmploymentPhaseV1.md)
`currentPlan` | [EmploymentPlanV1](EmploymentPlanV1.md)
`operations` | [EmploymentOperationsV1](EmploymentOperationsV1.md)
`sources` | [Array&lt;EmploymentSourceV1&gt;](EmploymentSourceV1.md)
`limitations` | Array&lt;string&gt;
`recommendedNextAction` | string
`availableCommands` | [Array&lt;AvailableCommandV1&gt;](AvailableCommandV1.md)
`authoritativeCursor` | string
`producedAt` | Date

## Example

```typescript
import type { EmploymentWorkspaceV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "schemaVersion": null,
  "protocolVersion": null,
  "relationshipId": null,
  "workspaceVersion": null,
  "agentType": null,
  "agentVersion": null,
  "manifestVersion": null,
  "readiness": null,
  "phases": null,
  "currentPlan": null,
  "operations": null,
  "sources": null,
  "limitations": null,
  "recommendedNextAction": null,
  "availableCommands": null,
  "authoritativeCursor": null,
  "producedAt": null,
} satisfies EmploymentWorkspaceV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentWorkspaceV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


