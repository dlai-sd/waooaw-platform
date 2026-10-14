# RelationshipWorkspacePreferencesV1

## Properties

| Name                              | Type    |
| --------------------------------- | ------- |
| `preferenceVersion`               | number  |
| `defaultFocus`                    | string  |
| `openProgressOnConversationFocus` | boolean |
| `updatedAt`                       | Date    |

## Example

```typescript
import type { RelationshipWorkspacePreferencesV1 } from "";

// TODO: Update the object below with actual values
const example = {
  preferenceVersion: null,
  defaultFocus: null,
  openProgressOnConversationFocus: null,
  updatedAt: null,
} satisfies RelationshipWorkspacePreferencesV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as RelationshipWorkspacePreferencesV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
