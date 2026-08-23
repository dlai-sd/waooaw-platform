targetScope = 'resourceGroup'

param storageAccountName string
param containerName string
param writerPrincipalId string
param writerRoleDefinitionId string

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: storageAccount
  name: 'default'
}

resource evidenceContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}

resource evidenceRetention 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2023-05-01' = {
  parent: evidenceContainer
  name: 'default'
  properties: {
    immutabilityPeriodSinceCreationInDays: 90
    allowProtectedAppendWrites: false
  }
}

resource evidenceWriterAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: evidenceContainer
  name: guid(evidenceContainer.id, writerPrincipalId, writerRoleDefinitionId)
  properties: {
    principalId: writerPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: writerRoleDefinitionId
  }
}

output containerId string = evidenceContainer.id
output containerUrl string = '${storageAccount.properties.primaryEndpoints.blob}${containerName}'