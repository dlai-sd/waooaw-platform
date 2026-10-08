
# SubmitPlanForReviewCommandV1


## Properties

Name | Type
------------ | -------------
`schemaVersion` | [EmploymentSchemaVersion](EmploymentSchemaVersion.md)
`kind` | string
`subjectRef` | string
`expectedWorkspaceVersion` | string
`expectedManifestVersion` | string
`expectedPlanVersion` | string

## Example

```typescript
import type { SubmitPlanForReviewCommandV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "schemaVersion": null,
  "kind": null,
  "subjectRef": null,
  "expectedWorkspaceVersion": null,
  "expectedManifestVersion": null,
  "expectedPlanVersion": null,
} satisfies SubmitPlanForReviewCommandV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SubmitPlanForReviewCommandV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


