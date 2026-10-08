
# CalendarCommitmentV1


## Properties

Name | Type
------------ | -------------
`commitmentId` | string
`timeZone` | string
`localDateTime` | string
`utcInstant` | Date
`utcOffset` | string
`fold` | number
`tzdbVersion` | string
`tolerancePolicy` | [CalendarTolerancePolicyRefV1](CalendarTolerancePolicyRefV1.md)
`recurrence` | string
`missedWindowPolicy` | string

## Example

```typescript
import type { CalendarCommitmentV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "commitmentId": null,
  "timeZone": null,
  "localDateTime": null,
  "utcInstant": null,
  "utcOffset": null,
  "fold": null,
  "tzdbVersion": null,
  "tolerancePolicy": null,
  "recurrence": null,
  "missedWindowPolicy": null,
} satisfies CalendarCommitmentV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CalendarCommitmentV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


