
# EmploymentCommandReceiptV1


## Properties

Name | Type
------------ | -------------
`schemaVersion` | [EmploymentSchemaVersion](EmploymentSchemaVersion.md)
`commandId` | string
`state` | [EmploymentCommandState](EmploymentCommandState.md)
`acceptedAt` | Date
`reconciliationUri` | string

## Example

```typescript
import type { EmploymentCommandReceiptV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "schemaVersion": null,
  "commandId": null,
  "state": null,
  "acceptedAt": null,
  "reconciliationUri": null,
} satisfies EmploymentCommandReceiptV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentCommandReceiptV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


