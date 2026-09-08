# NotificationPreferences

## Properties

| Name                   | Type                                                       |
| ---------------------- | ---------------------------------------------------------- |
| `approvalRequests`     | [Array&lt;NotificationChannel&gt;](NotificationChannel.md) |
| `maturityReports`      | [Array&lt;NotificationChannel&gt;](NotificationChannel.md) |
| `monthlyNarratives`    | [Array&lt;NotificationChannel&gt;](NotificationChannel.md) |
| `selfGovernanceAlerts` | [Array&lt;NotificationChannel&gt;](NotificationChannel.md) |

## Example

```typescript
import type { NotificationPreferences } from "";

// TODO: Update the object below with actual values
const example = {
  approvalRequests: null,
  maturityReports: null,
  monthlyNarratives: null,
  selfGovernanceAlerts: null,
} satisfies NotificationPreferences;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as NotificationPreferences;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
