targetScope = 'resourceGroup'

@allowed([
  'demo'
  'uat'
  'prod'
])
param environment string

@allowed(['INACTIVE'])
param activationState string = 'INACTIVE'

param location string = 'centralindia'
param stateStorageAccountId string
param bootstrapPrincipalId string
param bootstrapWriterRoleDefinitionId string
param cleanupDeleterRoleDefinitionId string
param runnerImage string
param reconcilerImage string

param runnerVnetAddressPrefix string = '10.70.0.0/24'
param runnerSubnetAddressPrefix string = '10.70.0.0/27'
param privateEndpointSubnetAddressPrefix string = '10.70.0.32/27'

var prefix = 'goal006-${environment}-runner'
var commonTags = {
  environment: environment
  goal: 'GOAL-006'
  'managed-by': 'azure-deployment-stacks'
  'runner-activation': activationState
}
var runnerSubnetId = '${runnerVnet.id}/subnets/runner'
var privateEndpointSubnetId = '${runnerVnet.id}/subnets/private-endpoints'
var keyVaultSecretsUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  tags: commonTags
  properties: {
    retentionInDays: 90
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource runnerNsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: '${prefix}-nsg'
  location: location
  tags: commonTags
  properties: {
    securityRules: [
      {
        name: 'deny-inbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'allow-vnet-https'
        properties: {
          priority: 100
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
      {
        name: 'allow-azure-dns'
        properties: {
          priority: 110
          direction: 'Outbound'
          access: 'Allow'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '53'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '168.63.129.16/32'
        }
      }
      {
        name: 'allow-required-https-egress'
        properties: {
          priority: 120
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: 'Internet'
        }
      }
      {
        name: 'deny-other-egress'
        properties: {
          priority: 4096
          direction: 'Outbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource runnerVnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${prefix}-vnet'
  location: location
  tags: commonTags
  properties: {
    addressSpace: {
      addressPrefixes: [runnerVnetAddressPrefix]
    }
    subnets: [
      {
        name: 'runner'
        properties: {
          addressPrefix: runnerSubnetAddressPrefix
          networkSecurityGroup: {
            id: runnerNsg.id
          }
          delegations: [
            {
              name: 'aca-environment'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'private-endpoints'
        properties: {
          addressPrefix: privateEndpointSubnetAddressPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          networkSecurityGroup: {
            id: runnerNsg.id
          }
        }
      }
    ]
  }
}

resource runnerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-identity'
  location: location
  tags: commonTags
}

resource cleanupIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-cleanup-identity'
  location: location
  tags: commonTags
}

resource runnerVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'waooaw-${environment}-runner-kv'
  location: location
  tags: commonTags
  properties: {
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
    }
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

resource runnerSecretAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: runnerVault
  name: guid(runnerVault.id, runnerIdentity.id, keyVaultSecretsUserRoleId)
  properties: {
    principalId: runnerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleId
  }
}

resource bootstrapSecretAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: runnerVault
  name: guid(runnerVault.id, bootstrapPrincipalId, bootstrapWriterRoleDefinitionId)
  properties: {
    principalId: bootstrapPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: bootstrapWriterRoleDefinitionId
  }
}

resource cleanupSecretAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: runnerVault
  name: guid(runnerVault.id, cleanupIdentity.id, cleanupDeleterRoleDefinitionId)
  properties: {
    principalId: cleanupIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cleanupDeleterRoleDefinitionId
  }
}

resource blobPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.blob.${az.environment().suffixes.storage}'
  location: 'global'
  tags: commonTags
}

resource vaultPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink${az.environment().suffixes.keyvaultDns}'
  location: 'global'
  tags: commonTags
}

resource blobDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: blobPrivateDns
  name: '${prefix}-blob-link'
  location: 'global'
  tags: commonTags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: runnerVnet.id
    }
  }
}

resource vaultDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: vaultPrivateDns
  name: '${prefix}-vault-link'
  location: 'global'
  tags: commonTags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: runnerVnet.id
    }
  }
}

resource statePrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${prefix}-state-pe'
  location: location
  tags: commonTags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'state-blob'
        properties: {
          privateLinkServiceId: stateStorageAccountId
          groupIds: ['blob']
        }
      }
    ]
  }
}

resource statePrivateDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: statePrivateEndpoint
  name: 'blob'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob'
        properties: {
          privateDnsZoneId: blobPrivateDns.id
        }
      }
    ]
  }
}

resource vaultPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${prefix}-vault-pe'
  location: location
  tags: commonTags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'runner-vault'
        properties: {
          privateLinkServiceId: runnerVault.id
          groupIds: ['vault']
        }
      }
    ]
  }
}

resource vaultPrivateDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: vaultPrivateEndpoint
  name: 'vault'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'vault'
        properties: {
          privateDnsZoneId: vaultPrivateDns.id
        }
      }
    ]
  }
}

resource runnerEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-aca'
  location: location
  tags: commonTags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: runnerSubnetId
      internal: true
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource runnerJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${prefix}-job'
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runnerIdentity.id}': {}
    }
  }
  properties: {
    environmentId: runnerEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 3600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'runner'
          image: runnerImage
          command: ['/bin/bash', '-lc']
          args: ['test "$RUNNER_ACTIVATION_STATE" = "ACTIVE" && test -n "$ACTIONS_RUNNER_INPUT_JITCONFIG" && exec ./run.sh --jitconfig "$ACTIONS_RUNNER_INPUT_JITCONFIG" || exit 0']
          env: [
            {
              name: 'RUNNER_ACTIVATION_STATE'
              value: activationState
            }
            {
              name: 'RUNNER_GROUP'
              value: 'goal006-${environment}-private'
            }
            {
              name: 'RUNNER_LABEL'
              value: 'goal006-${environment}-private'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
    }
  }
}

resource reconcilerJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${prefix}-reconciler'
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${cleanupIdentity.id}': {}
    }
  }
  properties: {
    environmentId: runnerEnvironment.id
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 120
      replicaRetryLimit: 0
      scheduleTriggerConfig: {
        cronExpression: '*/5 * * * *'
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'reconciler'
          image: reconcilerImage
          command: ['/bin/sh', '-c']
          args: ['test "$RUNNER_ACTIVATION_STATE" = "ACTIVE" && exit 64 || exit 0']
          env: [
            {
              name: 'RUNNER_ACTIVATION_STATE'
              value: activationState
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

output activationState string = activationState
output runnerResourceGroupId string = resourceGroup().id
output runnerVnetId string = runnerVnet.id
output runnerSubnetId string = runnerSubnetId
output statePrivateEndpointId string = statePrivateEndpoint.id
output runnerVaultId string = runnerVault.id
output runnerIdentityId string = runnerIdentity.id
output cleanupIdentityId string = cleanupIdentity.id
output runnerEnvironmentId string = runnerEnvironment.id
output runnerJobId string = runnerJob.id
output reconcilerJobId string = reconcilerJob.id