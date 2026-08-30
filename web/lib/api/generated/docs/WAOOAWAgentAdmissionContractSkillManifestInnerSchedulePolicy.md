# WAOOAWAgentAdmissionContractSkillManifestInnerSchedulePolicy

## Properties

| Name                     | Type              |
| ------------------------ | ----------------- |
| `mode`                   | string            |
| `customerAdjustable`     | boolean           |
| `minimumIntervalSeconds` | number            |
| `governedEvents`         | Set&lt;string&gt; |

## Example

```typescript
import type { WAOOAWAgentAdmissionContractSkillManifestInnerSchedulePolicy } from "";

// TODO: Update the object below with actual values
const example = {
  mode: null,
  customerAdjustable: null,
  minimumIntervalSeconds: null,
  governedEvents: null,
} satisfies WAOOAWAgentAdmissionContractSkillManifestInnerSchedulePolicy;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as WAOOAWAgentAdmissionContractSkillManifestInnerSchedulePolicy;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
