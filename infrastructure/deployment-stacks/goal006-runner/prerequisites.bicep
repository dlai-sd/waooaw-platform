targetScope = 'subscription'

@allowed([
  'demo'
  'uat'
  'prod'
])
param environment string

param location string = 'centralindia'
param runnerResourceGroupName string
param bootstrapPrincipalId string
param founderAlertEmail string
param budgetStartDate string
param monthlyBudgetInr int = 10000

var commonTags = {
  environment: environment
  goal: 'GOAL-006'
  'managed-by': 'goal006-bootstrap-prerequisites'
  'runner-activation': 'INACTIVE'
}
var bootstrapSecretWriterRoleSeed = environment == 'demo' ? 'goal006-bootstrap-secret-writer' : 'goal006-${environment}-bootstrap-secret-writer'
var cleanupSecretDeleterRoleSeed = environment == 'demo' ? 'goal006-cleanup-secret-deleter' : 'goal006-${environment}-cleanup-secret-deleter'
var bootstrapSecretWriterRoleName = guid(subscription().id, bootstrapSecretWriterRoleSeed)
var cleanupSecretDeleterRoleName = guid(subscription().id, cleanupSecretDeleterRoleSeed)
var deploymentStackOwnerRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'adb29209-aa1d-457b-a786-c913953d2891')

resource runnerResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: runnerResourceGroupName
  location: location
  tags: commonTags
}

resource bootstrapSecretWriterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: bootstrapSecretWriterRoleName
  properties: {
    roleName: 'GOAL-006 ${environment} Bootstrap Secret Writer'
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
    roleName: 'GOAL-006 ${environment} Cleanup Secret Deleter'
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

resource deploymentStackOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, bootstrapPrincipalId, deploymentStackOwnerRoleId)
  properties: {
    principalId: bootstrapPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: deploymentStackOwnerRoleId
  }
}

module runnerRoleAssignments 'prerequisites-rg.bicep' = {
  name: 'goal006-${environment}-runner-prerequisite-roles'
  scope: runnerResourceGroup
  params: {
    bootstrapPrincipalId: bootstrapPrincipalId
  }
}

output runnerResourceGroupId string = runnerResourceGroup.id
output bootstrapWriterRoleDefinitionId string = bootstrapSecretWriterRole.id
output cleanupDeleterRoleDefinitionId string = cleanupSecretDeleterRole.id