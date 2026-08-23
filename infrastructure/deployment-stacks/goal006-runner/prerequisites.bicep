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
var brokerSecretWriterRoleSeed = environment == 'demo' ? 'goal006-bootstrap-secret-writer' : 'goal006-${environment}-bootstrap-secret-writer'
var cleanupSecretDeleterRoleSeed = environment == 'demo' ? 'goal006-cleanup-secret-deleter' : 'goal006-${environment}-cleanup-secret-deleter'
var brokerSecretWriterRoleName = guid(subscription().id, brokerSecretWriterRoleSeed)
var cleanupSecretDeleterRoleName = guid(subscription().id, cleanupSecretDeleterRoleSeed)
var brokerJobOperatorRoleName = guid(subscription().id, 'goal006-${environment}-broker-job-operator')
var cleanupJobOperatorRoleName = guid(subscription().id, 'goal006-${environment}-cleanup-job-operator')
var deploymentStackOwnerRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'adb29209-aa1d-457b-a786-c913953d2891')

resource runnerResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: runnerResourceGroupName
  location: location
  tags: commonTags
}

resource brokerSecretWriterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: brokerSecretWriterRoleName
  properties: {
    roleName: 'GOAL-006 ${environment} Broker Secret Writer'
    description: 'Allow the private broker to set the short-lived runner registration secret without read, list, or delete authority.'
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

resource brokerJobOperatorRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: brokerJobOperatorRoleName
  properties: {
    roleName: 'GOAL-006 ${environment} Broker Job Operator'
    description: 'Read the runner job and executions and start one correlation-bound execution.'
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          'Microsoft.App/jobs/read'
          'Microsoft.App/jobs/executions/read'
          'Microsoft.App/jobs/start/action'
        ]
        notActions: []
        dataActions: []
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

resource cleanupJobOperatorRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: cleanupJobOperatorRoleName
  properties: {
    roleName: 'GOAL-006 ${environment} Cleanup Job Operator'
    description: 'Read runner jobs and cleanup logs, start the cleanup broker, or stop correlated executions during runner cleanup.'
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          'Microsoft.App/jobs/read'
          'Microsoft.App/jobs/executions/read'
          'Microsoft.App/jobs/getAuthToken/action'
          'Microsoft.App/jobs/start/action'
          'Microsoft.App/jobs/stop/execution/action'
        ]
        notActions: []
        dataActions: []
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
output brokerWriterRoleDefinitionId string = brokerSecretWriterRole.id
output brokerJobOperatorRoleDefinitionId string = brokerJobOperatorRole.id
output cleanupDeleterRoleDefinitionId string = cleanupSecretDeleterRole.id
output cleanupJobOperatorRoleDefinitionId string = cleanupJobOperatorRole.id