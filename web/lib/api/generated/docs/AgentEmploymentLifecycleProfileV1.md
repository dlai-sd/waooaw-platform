# AgentEmploymentLifecycleProfileV1

## Properties

| Name                  | Type                                                                               |
| --------------------- | ---------------------------------------------------------------------------------- |
| `agentInstanceId`     | string                                                                             |
| `relationshipVersion` | number                                                                             |
| `producedAt`          | Date                                                                               |
| `stages`              | [Array&lt;AgentEmploymentLifecycleStageV1&gt;](AgentEmploymentLifecycleStageV1.md) |

## Example

```typescript
import type { AgentEmploymentLifecycleProfileV1 } from "";

// TODO: Update the object below with actual values
const example = {
  agentInstanceId: null,
  relationshipVersion: null,
  producedAt: null,
  stages: null,
} satisfies AgentEmploymentLifecycleProfileV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as AgentEmploymentLifecycleProfileV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
