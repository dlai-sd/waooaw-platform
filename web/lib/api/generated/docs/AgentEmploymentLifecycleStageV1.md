# AgentEmploymentLifecycleStageV1

## Properties

| Name                   | Type                                                                        |
| ---------------------- | --------------------------------------------------------------------------- |
| `stage`                | string                                                                      |
| `state`                | [AgentEmploymentLifecycleStageState](AgentEmploymentLifecycleStageState.md) |
| `owner`                | string                                                                      |
| `inputRevisions`       | Array&lt;string&gt;                                                         |
| `outputRevision`       | string                                                                      |
| `evidenceState`        | [RelationshipEvidenceState](RelationshipEvidenceState.md)                   |
| `freshness`            | [RelationshipWorkspaceCurrencyState](RelationshipWorkspaceCurrencyState.md) |
| `completionCriteria`   | string                                                                      |
| `blockerReasons`       | Array&lt;string&gt;                                                         |
| `nextAuthorizedAction` | string                                                                      |

## Example

```typescript
import type { AgentEmploymentLifecycleStageV1 } from "";

// TODO: Update the object below with actual values
const example = {
  stage: null,
  state: null,
  owner: null,
  inputRevisions: null,
  outputRevision: null,
  evidenceState: null,
  freshness: null,
  completionCriteria: null,
  blockerReasons: null,
  nextAuthorizedAction: null,
} satisfies AgentEmploymentLifecycleStageV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as AgentEmploymentLifecycleStageV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
