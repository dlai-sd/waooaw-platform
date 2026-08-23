targetScope = 'resourceGroup'

@allowed([
  'demo'
  'uat'
  'prod'
])
param environment string

@allowed(['INACTIVE', 'ACTIVE'])
param activationState string = 'INACTIVE'

param location string = 'centralindia'
param stateStorageAccountId string
param brokerWriterRoleDefinitionId string
param brokerJobOperatorRoleDefinitionId string
param cleanupDeleterRoleDefinitionId string
param cleanupJobOperatorRoleDefinitionId string
param evidenceWriterRoleDefinitionId string
param runnerImage string
param reconcilerImage string
param githubAppId string
param githubAppInstallationId string
param githubAppKeyName string
param githubAppKeyVersion string
param runnerTokenSecretName string = 'runner-registration-token'
param cleanupFederatedSubject string = 'repo:dlai-sd/waooaw-platform:environment:${environment}'

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
var keyVaultCryptoUserRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '12338af0-0e69-4776-bea7-57ae8d297424')
var keyVaultCryptoOfficerRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '14b46e9e-c2b7-41b4-b07b-48a6ebf60603')
var stateStorageAccountSegments = split(stateStorageAccountId, '/')

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

resource brokerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-broker-identity'
  location: location
  tags: commonTags
}

resource cleanupIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-cleanup-identity'
  location: location
  tags: commonTags
}

resource evidenceWriterIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-evidence-writer-identity'
  location: location
  tags: commonTags
}

resource keyImportIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-key-import-identity'
  location: location
  tags: commonTags
}

resource cleanupFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: cleanupIdentity
  name: 'github-${environment}-runner-cleanup'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: cleanupFederatedSubject
    audiences: ['api://AzureADTokenExchange']
  }
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

resource runnerVaultDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: runnerVault
  name: '${prefix}-vault-audit'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      {
        category: 'AuditEvent'
        enabled: true
      }
    ]
  }
}

module stateBlobDiagnostics 'blob-diagnostics.bicep' = {
  scope: resourceGroup(stateStorageAccountSegments[2], stateStorageAccountSegments[4])
  name: '${prefix}-blob-diagnostics'
  params: {
    diagnosticSettingName: '${prefix}-blob-audit'
    storageAccountName: stateStorageAccountSegments[8]
    workspaceId: logAnalytics.id
  }
}

module cleanupEvidenceStorage 'cleanup-evidence-storage.bicep' = {
  scope: resourceGroup(stateStorageAccountSegments[2], stateStorageAccountSegments[4])
  name: '${prefix}-cleanup-evidence-storage'
  params: {
    storageAccountName: stateStorageAccountSegments[8]
    containerName: 'goal006-${environment}-runner-evidence'
    writerPrincipalId: evidenceWriterIdentity.properties.principalId
    writerRoleDefinitionId: evidenceWriterRoleDefinitionId
  }
}

resource githubAppKey 'Microsoft.KeyVault/vaults/keys@2023-07-01' existing = {
  parent: runnerVault
  name: githubAppKeyName
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

resource brokerSecretAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: runnerVault
  name: guid(runnerVault.id, brokerIdentity.id, brokerWriterRoleDefinitionId)
  properties: {
    principalId: brokerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: brokerWriterRoleDefinitionId
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

resource keyImportAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: runnerVault
  name: guid(runnerVault.id, keyImportIdentity.id, keyVaultCryptoOfficerRoleId)
  properties: {
    principalId: keyImportIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultCryptoOfficerRoleId
  }
}

resource brokerKeySignAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (activationState == 'ACTIVE') {
  scope: githubAppKey
  name: guid(githubAppKey.id, brokerIdentity.id, keyVaultCryptoUserRoleId)
  properties: {
    principalId: brokerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultCryptoUserRoleId
  }
}

resource cleanupKeySignAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (activationState == 'ACTIVE') {
  scope: githubAppKey
  name: guid(githubAppKey.id, cleanupIdentity.id, keyVaultCryptoUserRoleId)
  properties: {
    principalId: cleanupIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultCryptoUserRoleId
  }
}

resource cleanupJobControl 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, cleanupIdentity.id, cleanupJobOperatorRoleDefinitionId)
  properties: {
    principalId: cleanupIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: cleanupJobOperatorRoleDefinitionId
  }
}

resource blobPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.blob.${az.environment().suffixes.storage}'
  location: 'global'
  tags: commonTags
}

resource vaultPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
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
  name: '${prefix}-vaultcore-pe'
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
          command: ['/opt/waooaw/entrypoint.sh']
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: runnerIdentity.properties.clientId
            }
            {
              name: 'RUNNER_ACTIVATION_STATE'
              value: activationState
            }
            {
              name: 'RUNNER_LABEL'
              value: 'goal006-${environment}-private'
            }
            {
              name: 'RUNNER_VAULT_URL'
              value: runnerVault.properties.vaultUri
            }
            {
              name: 'RUNNER_TOKEN_SECRET_NAME'
              value: runnerTokenSecretName
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

resource keyImportApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${prefix}-key-import'
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${keyImportIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: runnerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [
        {
          name: 'key-import'
          image: runnerImage
          command: ['tail', '-f', '/dev/null']
          env: [
            { name: 'AZURE_CLIENT_ID', value: keyImportIdentity.properties.clientId }
            { name: 'RUNNER_VAULT_NAME', value: runnerVault.name }
            { name: 'GITHUB_APP_KEY_NAME', value: 'github-runner-app-signing' }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource brokerJobControl 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: runnerJob
  name: guid(runnerJob.id, brokerIdentity.id, brokerJobOperatorRoleDefinitionId)
  properties: {
    principalId: brokerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: brokerJobOperatorRoleDefinitionId
  }
}

resource brokerJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${prefix}-broker'
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${brokerIdentity.id}': {}
    }
  }
  properties: {
    environmentId: runnerEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 300
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'broker'
          image: runnerImage
          command: ['python3', '/opt/waooaw/goal006_runner_lifecycle.py']
          args: ['start', '--app-manifest', '/opt/waooaw/github-runner-app-manifest.json', '--output', '/home/runner/lifecycle-record.json']
          env: [
            { name: 'AZURE_CLIENT_ID', value: brokerIdentity.properties.clientId }
            { name: 'RUNNER_ACTIVATION_STATE', value: activationState }
            { name: 'RUNNER_ENVIRONMENT', value: environment }
            { name: 'GITHUB_REPOSITORY', value: 'dlai-sd/waooaw-platform' }
            { name: 'GITHUB_RUN_ID', value: 'PENDING_EXECUTION_OVERRIDE' }
            { name: 'GITHUB_RUN_ATTEMPT', value: 'PENDING_EXECUTION_OVERRIDE' }
            { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
            { name: 'RUNNER_RESOURCE_GROUP', value: resourceGroup().name }
            { name: 'RUNNER_JOB_NAME', value: runnerJob.name }
            { name: 'RUNNER_VAULT_URL', value: runnerVault.properties.vaultUri }
            { name: 'RUNNER_TOKEN_SECRET_NAME', value: runnerTokenSecretName }
            { name: 'GITHUB_APP_ID', value: githubAppId }
            { name: 'GITHUB_APP_INSTALLATION_ID', value: githubAppInstallationId }
            { name: 'GITHUB_APP_KEY_ID', value: '${runnerVault.properties.vaultUri}keys/${githubAppKeyName}/${githubAppKeyVersion}' }
            { name: 'RUNNER_LABEL', value: 'goal006-${environment}-private' }
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

resource cleanupBrokerJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${prefix}-cleanup'
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${cleanupIdentity.id}': {}
      '${evidenceWriterIdentity.id}': {}
    }
  }
  properties: {
    environmentId: runnerEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 300
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'cleanup-broker'
          image: runnerImage
          command: ['python3', '/opt/waooaw/goal006_runner_lifecycle.py']
          args: ['cleanup-correlated', '--app-manifest', '/opt/waooaw/github-runner-app-manifest.json', '--private-job-conclusion', 'PENDING_EXECUTION_OVERRIDE', '--output', '/home/runner/cleanup-record.json']
          env: [
            { name: 'AZURE_CLIENT_ID', value: cleanupIdentity.properties.clientId }
            { name: 'EVIDENCE_WRITER_CLIENT_ID', value: evidenceWriterIdentity.properties.clientId }
            { name: 'RUNNER_EVIDENCE_CONTAINER_URL', value: cleanupEvidenceStorage.outputs.containerUrl }
            { name: 'RUNNER_ACTIVATION_STATE', value: activationState }
            { name: 'RUNNER_ENVIRONMENT', value: environment }
            { name: 'GITHUB_REPOSITORY', value: 'dlai-sd/waooaw-platform' }
            { name: 'GITHUB_RUN_ID', value: 'PENDING_EXECUTION_OVERRIDE' }
            { name: 'GITHUB_RUN_ATTEMPT', value: 'PENDING_EXECUTION_OVERRIDE' }
            { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
            { name: 'RUNNER_RESOURCE_GROUP', value: resourceGroup().name }
            { name: 'RUNNER_JOB_NAME', value: runnerJob.name }
            { name: 'RUNNER_VAULT_URL', value: runnerVault.properties.vaultUri }
            { name: 'RUNNER_TOKEN_SECRET_NAME', value: runnerTokenSecretName }
            { name: 'GITHUB_APP_ID', value: githubAppId }
            { name: 'GITHUB_APP_INSTALLATION_ID', value: githubAppInstallationId }
            { name: 'GITHUB_APP_KEY_ID', value: '${runnerVault.properties.vaultUri}keys/${githubAppKeyName}/${githubAppKeyVersion}' }
            { name: 'RUNNER_LABEL', value: 'goal006-${environment}-private' }
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
    configuration: union({
      triggerType: activationState == 'ACTIVE' ? 'Schedule' : 'Manual'
      replicaTimeout: 120
      replicaRetryLimit: 0
    }, activationState == 'ACTIVE' ? {
      scheduleTriggerConfig: {
        cronExpression: '*/5 * * * *'
        parallelism: 1
        replicaCompletionCount: 1
      }
    } : {
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    })
    template: {
      containers: [
        {
          name: 'reconciler'
          image: reconcilerImage
          command: ['python3', '-c']
          args: [
            loadTextContent('../../../scripts/goal006_runner_lifecycle.py')
            'reconcile'
            '--app-manifest-json'
            loadTextContent('../../../architecture/reference/pipeline/github-runner-app-manifest.json')
            '--output'
            '/tmp/reconciliation-record.json'
          ]
          env: [
            { name: 'AZURE_CLIENT_ID', value: cleanupIdentity.properties.clientId }
            { name: 'RUNNER_ACTIVATION_STATE', value: activationState }
            { name: 'RUNNER_ENVIRONMENT', value: environment }
            { name: 'GITHUB_REPOSITORY', value: 'dlai-sd/waooaw-platform' }
            { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
            { name: 'RUNNER_RESOURCE_GROUP', value: resourceGroup().name }
            { name: 'RUNNER_JOB_NAME', value: runnerJob.name }
            { name: 'RUNNER_VAULT_URL', value: runnerVault.properties.vaultUri }
            { name: 'RUNNER_TOKEN_SECRET_NAME', value: runnerTokenSecretName }
            { name: 'GITHUB_APP_ID', value: githubAppId }
            { name: 'GITHUB_APP_INSTALLATION_ID', value: githubAppInstallationId }
            { name: 'GITHUB_APP_KEY_ID', value: '${runnerVault.properties.vaultUri}keys/${githubAppKeyName}/${githubAppKeyVersion}' }
            { name: 'RUNNER_LABEL', value: 'goal006-${environment}-private' }
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
output brokerIdentityId string = brokerIdentity.id
output brokerIdentityClientId string = brokerIdentity.properties.clientId
output cleanupIdentityId string = cleanupIdentity.id
output cleanupIdentityClientId string = cleanupIdentity.properties.clientId
output evidenceWriterIdentityId string = evidenceWriterIdentity.id
output evidenceWriterIdentityClientId string = evidenceWriterIdentity.properties.clientId
output cleanupEvidenceContainerId string = cleanupEvidenceStorage.outputs.containerId
output cleanupEvidenceContainerUrl string = cleanupEvidenceStorage.outputs.containerUrl
output keyImportIdentityId string = keyImportIdentity.id
output runnerVaultUri string = runnerVault.properties.vaultUri
output runnerEnvironmentId string = runnerEnvironment.id
output runnerJobId string = runnerJob.id
output brokerJobId string = brokerJob.id
output cleanupBrokerJobId string = cleanupBrokerJob.id
output reconcilerJobId string = reconcilerJob.id
output keyImportAppId string = keyImportApp.id