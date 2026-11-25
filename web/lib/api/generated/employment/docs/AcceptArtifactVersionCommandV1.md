
# AcceptArtifactVersionCommandV1

Approval of one exact locked-artifact version: \'Do you approve this exact version?\' Recorded as an APPROVAL bound to the artifact id and digest.

## Properties

Name | Type
------------ | -------------
`schemaVersion` | [EmploymentSchemaVersion](EmploymentSchemaVersion.md)
`kind` | string
`subjectRef` | string
`expectedWorkspaceVersion` | string
`expectedManifestVersion` | string
`expectedArtifactId` | string
`expectedArtifactDigest` | string
`acknowledgement` | string

## Example

```typescript
import type { AcceptArtifactVersionCommandV1 } from '@waooaw/employment-client'

// TODO: Update the object below with actual values
const example = {
  "schemaVersion": null,
  "kind": null,
  "subjectRef": null,
  "expectedWorkspaceVersion": null,
  "expectedManifestVersion": null,
  "expectedArtifactId": null,
  "expectedArtifactDigest": null,
  "acknowledgement": null,
} satisfies AcceptArtifactVersionCommandV1

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AcceptArtifactVersionCommandV1
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


