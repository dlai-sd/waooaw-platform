
# EmploymentPhaseOwnerSummaryV1


## Properties

Name | Type
------------ | -------------
`owner` | string
`state` | [SourceState](SourceState.md)
`label` | string
`source` | [EmploymentSourceV1](EmploymentSourceV1.md)
`limitation` | string

## Example

```typescript
import type { EmploymentPhaseOwnerSummaryV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "owner": null,
  "state": null,
  "label": null,
  "source": null,
  "limitation": null,
} satisfies EmploymentPhaseOwnerSummaryV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentPhaseOwnerSummaryV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


