targetScope = 'subscription'

@allowed([
  'demo'
  'uat'
  'prod'
])
param environment string

@allowed(['INACTIVE'])
param activationState string = 'INACTIVE'

param location string = 'centralindia'
param runnerResourceGroupName string
param stateStorageAccountId string
param bootstrapPrincipalId string
param runnerImage string
param reconcilerImage string
param runnerVnetAddressPrefix string
param runnerSubnetAddressPrefix string
param privateEndpointSubnetAddressPrefix string
var bootstrapSecretWriterRoleSeed = environment == 'demo' ? 'goal006-bootstrap-secret-writer' : 'goal006-${environment}-bootstrap-secret-writer'
var cleanupSecretDeleterRoleSeed = environment == 'demo' ? 'goal006-cleanup-secret-deleter' : 'goal006-${environment}-cleanup-secret-deleter'
var bootstrapSecretWriterRoleName = guid(subscription().id, bootstrapSecretWriterRoleSeed)
var cleanupSecretDeleterRoleName = guid(subscription().id, cleanupSecretDeleterRoleSeed)

resource runnerResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' existing = {
  name: runnerResourceGroupName
}

resource bootstrapSecretWriterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: bootstrapSecretWriterRoleName
}

resource cleanupSecretDeleterRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  name: cleanupSecretDeleterRoleName
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