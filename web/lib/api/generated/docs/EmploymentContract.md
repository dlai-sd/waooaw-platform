# EmploymentContract

## Properties

| Name               | Type                                         |
| ------------------ | -------------------------------------------- |
| `id`               | string                                       |
| `tenantId`         | string                                       |
| `professionalId`   | string                                       |
| `decisionSpaceId`  | string                                       |
| `state`            | [EmploymentState](EmploymentState.md)        |
| `authorityLevel`   | number                                       |
| `goals`            | [Array&lt;BusinessGoal&gt;](BusinessGoal.md) |
| `reviewCadence`    | [ReviewCadence](ReviewCadence.md)            |
| `isTrial`          | boolean                                      |
| `trialEndsAt`      | Date                                         |
| `trialConvertedAt` | Date                                         |
| `createdAt`        | Date                                         |
| `activatedAt`      | Date                                         |
| `suspendedAt`      | Date                                         |
| `terminatedAt`     | Date                                         |

## Example

```typescript
import type { EmploymentContract } from "";

// TODO: Update the object below with actual values
const example = {
  id: null,
  tenantId: null,
  professionalId: null,
  decisionSpaceId: null,
  state: null,
  authorityLevel: null,
  goals: null,
  reviewCadence: null,
  isTrial: null,
  trialEndsAt: null,
  trialConvertedAt: null,
  createdAt: null,
  activatedAt: null,
  suspendedAt: null,
  terminatedAt: null,
} satisfies EmploymentContract;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as EmploymentContract;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
