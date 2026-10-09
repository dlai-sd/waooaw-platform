
# EmploymentSourceV1


## Properties

Name | Type
------------ | -------------
`owner` | string
`contractVersion` | string
`sourceVersion` | string
`state` | [SourceState](SourceState.md)
`observedAt` | Date
`validUntil` | Date
`limitation` | string

## Example

```typescript
import type { EmploymentSourceV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "owner": null,
  "contractVersion": null,
  "sourceVersion": null,
  "state": null,
  "observedAt": null,
  "validUntil": null,
  "limitation": null,
} satisfies EmploymentSourceV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentSourceV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


