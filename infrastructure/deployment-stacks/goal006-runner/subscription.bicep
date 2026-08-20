targetScope = 'subscription'

@allowed(['demo'])
param environment string

@allowed(['INACTIVE'])
param activationState string = 'INACTIVE'

param location string = 'centralindia'
param runnerResourceGroupName string
param stateStorageAccountId string
param bootstrapPrincipalId string
param runnerImage string
param reconcilerImage string
param founderAlertEmail string
param budgetStartDate string
param runnerVnetAddressPrefix string
param runnerSubnetAddressPrefix string
param privateEndpointSubnetAddressPrefix string
param monthlyBudgetInr int = 10000

var commonTags = {
  environment: environment
  goal: 'GOAL-006'
  'managed-by': 'azure-deployment-stacks'
  'runner-activation': activationState
}
var bootstrapSecretWriterRoleName = guid(subscription().id, 'goal006-bootstrap-secret-writer')
var cleanupSecretDeleterRoleName = guid(subscription().id, 'goal006-cleanup-secret-deleter')

resource runnerResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: runnerResourceGroupName
  location: location
  tags: commonTags
}

resource bootstrapSecretWriterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: bootstrapSecretWriterRoleName
  properties: {
    roleName: 'GOAL-006 Bootstrap Secret Writer'
    description: 'Set the short-lived environment runner registration secret without read, list, or delete authority.'
    type: 'CustomRole'
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: ['Microsoft.KeyVault/vaults/secrets/setSecret/action']
        notDataActions: []
      }
    ]
    assignableScopes: [runnerResourceGroup.id]
  }
}

resource cleanupSecretDeleterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: cleanupSecretDeleterRoleName
  properties: {
    roleName: 'GOAL-006 Cleanup Secret Deleter'
    description: 'Delete the short-lived environment runner registration secret without read, list, or write authority.'
    type: 'CustomRole'
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: ['Microsoft.KeyVault/vaults/secrets/delete']
        notDataActions: []
      }
    ]
    assignableScopes: [runnerResourceGroup.id]
  }
}

resource monthlyBudget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: 'goal006-cumulative-monthly'
  properties: {
    amount: monthlyBudgetInr
    category: 'Cost'
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
      endDate: '2030-08-01T00:00:00Z'
    }
    filter: {
      tags: {
        name: 'goal'
        operator: 'In'
        values: ['GOAL-006']
      }
    }
    notifications: {
      Actual_GreaterThan_50_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 50
        contactEmails: [founderAlertEmail]
      }
      Actual_GreaterThan_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: [founderAlertEmail]
      }
      Actual_GreaterThan_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        contactEmails: [founderAlertEmail]
      }
    }
  }
}

module runnerControlPlane 'main.bicep' = {
  name: 'goal006-${environment}-runner-control-plane'
  scope: runnerResourceGroup
  params: {
    environment: environment
    activationState: activationState
    location: location
    stateStorageAccountId: stateStorageAccountId
    bootstrapPrincipalId: bootstrapPrincipalId
    bootstrapWriterRoleDefinitionId: bootstrapSecretWriterRole.id
    cleanupDeleterRoleDefinitionId: cleanupSecretDeleterRole.id
    runnerImage: runnerImage
    reconcilerImage: reconcilerImage
    runnerVnetAddressPrefix: runnerVnetAddressPrefix
    runnerSubnetAddressPrefix: runnerSubnetAddressPrefix
    privateEndpointSubnetAddressPrefix: privateEndpointSubnetAddressPrefix
  }
}

output activationState string = runnerControlPlane.outputs.activationState
output runnerResourceGroupId string = runnerControlPlane.outputs.runnerResourceGroupId
output runnerVnetId string = runnerControlPlane.outputs.runnerVnetId
output runnerSubnetId string = runnerControlPlane.outputs.runnerSubnetId
output statePrivateEndpointId string = runnerControlPlane.outputs.statePrivateEndpointId
output runnerVaultId string = runnerControlPlane.outputs.runnerVaultId
output runnerIdentityId string = runnerControlPlane.outputs.runnerIdentityId
output cleanupIdentityId string = runnerControlPlane.outputs.cleanupIdentityId
output runnerEnvironmentId string = runnerControlPlane.outputs.runnerEnvironmentId
output runnerJobId string = runnerControlPlane.outputs.runnerJobId
output reconcilerJobId string = runnerControlPlane.outputs.reconcilerJobId