
# RequirementProgressV1


## Properties

Name | Type
------------ | -------------
`mandatoryTotal` | number
`mandatoryCompleted` | number
`optionalTotal` | number
`optionalCompleted` | number
`blockedCount` | number
`deferredCount` | number

## Example

```typescript
import type { RequirementProgressV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "mandatoryTotal": null,
  "mandatoryCompleted": null,
  "optionalTotal": null,
  "optionalCompleted": null,
  "blockedCount": null,
  "deferredCount": null,
} satisfies RequirementProgressV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RequirementProgressV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


