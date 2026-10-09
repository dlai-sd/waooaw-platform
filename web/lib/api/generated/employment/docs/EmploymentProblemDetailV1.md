
# EmploymentProblemDetailV1


## Properties

Name | Type
------------ | -------------
`type` | string
`title` | string
`status` | number
`detail` | string
`code` | [EmploymentProblemCode](EmploymentProblemCode.md)
`correlationId` | string
`reconciliationUri` | string
`currentWorkspaceVersion` | string
`currentPlanVersion` | string

## Example

```typescript
import type { EmploymentProblemDetailV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "type": null,
  "title": null,
  "status": null,
  "detail": null,
  "code": null,
  "correlationId": null,
  "reconciliationUri": null,
  "currentWorkspaceVersion": null,
  "currentPlanVersion": null,
} satisfies EmploymentProblemDetailV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentProblemDetailV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


