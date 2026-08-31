# ProfessionalSkillDisclosure

## Properties

| Name                  | Type    |
| --------------------- | ------- |
| `skillId`             | string  |
| `displayName`         | string  |
| `applicableInTrial`   | boolean |
| `activationCondition` | string  |

## Example

```typescript
import type { ProfessionalSkillDisclosure } from "";

// TODO: Update the object below with actual values
const example = {
  skillId: null,
  displayName: null,
  applicableInTrial: null,
  activationCondition: null,
} satisfies ProfessionalSkillDisclosure;

console.log(example);

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example);
console.log(exampleJSON);

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProfessionalSkillDisclosure;
console.log(exampleParsed);
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)
