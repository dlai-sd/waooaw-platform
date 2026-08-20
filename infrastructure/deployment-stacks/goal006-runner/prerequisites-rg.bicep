targetScope = 'resourceGroup'

param bootstrapPrincipalId string

var contributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
var rbacAdministratorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'f58310d9-a9f6-439a-9e8d-f62e7b41a168')

resource runnerContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, bootstrapPrincipalId, contributorRoleId)
  properties: {
    principalId: bootstrapPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: contributorRoleId
  }
}

resource runnerRbacAdministrator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, bootstrapPrincipalId, rbacAdministratorRoleId)
  properties: {
    principalId: bootstrapPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: rbacAdministratorRoleId
  }
}