
# EmploymentWorkspaceItemV1


## Properties

Name | Type
------------ | -------------
`itemId` | string
`itemVersion` | string
`phase` | [EmploymentPhaseKind](EmploymentPhaseKind.md)
`label` | string
`mandatory` | boolean
`state` | [EmploymentItemState](EmploymentItemState.md)
`reason` | string
`accountableOwner` | string
`dueMeaning` | string
`blockedEffects` | [Array&lt;BlockedEffectV1&gt;](BlockedEffectV1.md)
`completionReference` | string
`source` | [EmploymentSourceV1](EmploymentSourceV1.md)
`availableCommands` | [Array&lt;AvailableCommandV1&gt;](AvailableCommandV1.md)

## Example

```typescript
import type { EmploymentWorkspaceItemV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "itemId": null,
  "itemVersion": null,
  "phase": null,
  "label": null,
  "mandatory": null,
  "state": null,
  "reason": null,
  "accountableOwner": null,
  "dueMeaning": null,
  "blockedEffects": null,
  "completionReference": null,
  "source": null,
  "availableCommands": null,
} satisfies EmploymentWorkspaceItemV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentWorkspaceItemV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


