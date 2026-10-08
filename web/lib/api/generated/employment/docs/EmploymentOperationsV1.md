
# EmploymentOperationsV1


## Properties

Name | Type
------------ | -------------
`mode` | [EmploymentOperationMode](EmploymentOperationMode.md)
`eligibility` | [OperationsEligibilityState](OperationsEligibilityState.md)
`eligibleSkillRefs` | Array&lt;string&gt;
`lockedSkillRefs` | Array&lt;string&gt;
`permittedOperationClasses` | Set&lt;string&gt;
`stopReachable` | boolean
`commercialSource` | [EmploymentSourceV1](EmploymentSourceV1.md)

## Example

```typescript
import type { EmploymentOperationsV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "mode": null,
  "eligibility": null,
  "eligibleSkillRefs": null,
  "lockedSkillRefs": null,
  "permittedOperationClasses": null,
  "stopReachable": null,
  "commercialSource": null,
} satisfies EmploymentOperationsV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentOperationsV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


