# EmploymentRelationshipCollectionV1

## Properties

| Name                  | Type                                                                               |
| --------------------- | ---------------------------------------------------------------------------------- |
| `schemaVersion`       | [CustomerPortalSchemaVersion](CustomerPortalSchemaVersion.md)                      |
| `producedAt`          | Date                                                                               |
| `nextCursor`          | string                                                                             |
| `defaultResumeTarget` | [CustomerPortalDestinationV1](CustomerPortalDestinationV1.md)                      |
| `items`               | [Array&lt;EmploymentRelationshipSummaryV1&gt;](EmploymentRelationshipSummaryV1.md) |

## Example

```typescript
import type { EmploymentRelationshipCollectionV1 } from "";

// TODO: Update the object below with actual values
const example = {
  schemaVersion: null,
  producedAt: null,
  nextCursor: null,
  defaultResumeTarget: null,
  items: null,
} satisfies EmploymentRelationshipCollectionV1;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(
  exampleJSON,
) as EmploymentRelationshipCollectionV1;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
