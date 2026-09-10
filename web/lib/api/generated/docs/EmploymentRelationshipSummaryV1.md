# EmploymentRelationshipSummaryV1

## Properties

| Name                             | Type                                                                                      |
| -------------------------------- | ----------------------------------------------------------------------------------------- |
| `relationshipId`                 | string                                                                                    |
| `agentInstanceId`                | string                                                                                    |
| `professionalAdmissionId`        | string                                                                                    |
| `professionalType`               | string                                                                                    |
| `professionalVersion`            | string                                                                                    |
| `professionalDisplayName`        | string                                                                                    |
| `lifecycleState`                 | [EmploymentRelationshipState](EmploymentRelationshipState.md)                             |
| `currentGoalSummary`             | string                                                                                    |
| `unreadState`                    | string                                                                                    |
| `availabilityState`              | [EmploymentRelationshipAvailabilityStateV1](EmploymentRelationshipAvailabilityStateV1.md) |
| `currencyState`                  | [RelationshipWorkspaceCurrencyState](RelationshipWorkspaceCurrencyState.md)               |
| `lastAuthoritativelyConfirmedAt` | Date                                                                                      |
| `resumeTarget`                   | [CustomerPortalDestinationV1](CustomerPortalDestinationV1.md)                             |

## Example

```typescript
import type { EmploymentRelationshipSummaryV1 } from "";

// TODO: Update the object below with actual values
const example = {
  relationshipId: null,
  agentInstanceId: null,
  professionalAdmissionId: null,
  professionalType: null,
  professionalVersion: null,
  professionalDisplayName: null,
  lifecycleState: null,
  currentGoalSummary: null,
  unreadState: null,
  availabilityState: null,
  currencyState: null,
  lastAuthoritativelyConfirmedAt: null,
  resumeTarget: null,
} satisfies EmploymentRelationshipSummaryV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as EmploymentRelationshipSummaryV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
