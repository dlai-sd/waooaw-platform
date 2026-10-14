# WorkspaceLayoutPreferencesV1

## Properties

| Name                       | Type                                    |
| -------------------------- | --------------------------------------- |
| `schemaVersion`            | string                                  |
| `preferenceVersion`        | number                                  |
| `navigationVisibility`     | [PaneVisibilityV1](PaneVisibilityV1.md) |
| `progressVisibility`       | [PaneVisibilityV1](PaneVisibilityV1.md) |
| `conversationWidthPercent` | number                                  |
| `reduceMotion`             | boolean                                 |
| `updatedAt`                | Date                                    |

## Example

```typescript
import type { WorkspaceLayoutPreferencesV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  preferenceVersion: null,
  navigationVisibility: null,
  progressVisibility: null,
  conversationWidthPercent: null,
  reduceMotion: null,
  updatedAt: null,
} satisfies WorkspaceLayoutPreferencesV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as WorkspaceLayoutPreferencesV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
