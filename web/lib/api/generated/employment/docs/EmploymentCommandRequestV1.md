
# EmploymentCommandRequestV1


## Properties

Name | Type
------------ | -------------
`schemaVersion` | [EmploymentSchemaVersion](EmploymentSchemaVersion.md)
`kind` | string
`subjectRef` | string
`expectedWorkspaceVersion` | string
`expectedManifestVersion` | string
`deferredReason` | string
`blockedSkillRefs` | Set&lt;string&gt;
`candidatePatchRef` | string
`expectedPlanVersion` | string
`expectedDecisionSpaceVersion` | number
`expectedWbeSourceVersion` | string
`acknowledgement` | string
`requestedCalendarCommitment` | [CalendarCommitmentV1](CalendarCommitmentV1.md)

## Example

```typescript
import type { EmploymentCommandRequestV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "schemaVersion": null,
  "kind": null,
  "subjectRef": null,
  "expectedWorkspaceVersion": null,
  "expectedManifestVersion": null,
  "deferredReason": null,
  "blockedSkillRefs": null,
  "candidatePatchRef": null,
  "expectedPlanVersion": null,
  "expectedDecisionSpaceVersion": null,
  "expectedWbeSourceVersion": null,
  "acknowledgement": null,
  "requestedCalendarCommitment": null,
} satisfies EmploymentCommandRequestV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentCommandRequestV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


