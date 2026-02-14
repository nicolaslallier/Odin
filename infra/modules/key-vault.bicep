@description('Name of the Key Vault')
param name string

@description('Azure region')
param location string = resourceGroup().location

@description('Enable RBAC authorization (recommended; no access policies)')
param enableRbacAuthorization bool = true

@description('Resource tags')
param tags object = {}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: enableRbacAuthorization
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
  }
}

output id string = keyVault.id
output name string = keyVault.name
output vaultUri string = keyVault.properties.vaultUri
