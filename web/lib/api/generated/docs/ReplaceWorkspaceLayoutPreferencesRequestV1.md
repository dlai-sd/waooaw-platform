# ReplaceWorkspaceLayoutPreferencesRequestV1

## Properties

| Name                       | Type                                    |
| -------------------------- | --------------------------------------- |
| `expectedVersion`          | number                                  |
| `navigationVisibility`     | [PaneVisibilityV1](PaneVisibilityV1.md) |
| `progressVisibility`       | [PaneVisibilityV1](PaneVisibilityV1.md) |
| `conversationWidthPercent` | number                                  |
| `reduceMotion`             | boolean                                 |

## Example

```typescript
import type { ReplaceWorkspaceLayoutPreferencesRequestV1 } from "";

// TODO: Update the object below with actual values
const example = {
  expectedVersion: null,
  navigationVisibility: null,
  progressVisibility: null,
  conversationWidthPercent: null,
  reduceMotion: null,
} satisfies ReplaceWorkspaceLayoutPreferencesRequestV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as ReplaceWorkspaceLayoutPreferencesRequestV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
