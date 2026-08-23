targetScope = 'resourceGroup'

param diagnosticSettingName string
param storageAccountName string
param workspaceId string

resource stateStorageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource stateBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: stateStorageAccount
  name: 'default'
}

resource stateBlobDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: stateBlobService
  name: diagnosticSettingName
  properties: {
    workspaceId: workspaceId
    logs: [
      {
        category: 'StorageRead'
        enabled: true
      }
      {
        category: 'StorageWrite'
        enabled: true
      }
      {
        category: 'StorageDelete'
        enabled: true
      }
    ]
  }
}