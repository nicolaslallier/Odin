@description('Name of the storage account')
param name string

@description('Azure region')
param location string = resourceGroup().location

@description('SKU: Standard_LRS, Standard_GRS, Standard_RAGRS, Premium_LRS')
param sku string = 'Standard_LRS'

@description('Kind: Storage, StorageV2, BlobStorage')
param kind string = 'StorageV2'

@description('Resource tags')
param tags object = {}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  kind: kind
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

output id string = storageAccount.id
output name string = storageAccount.name
output primaryEndpoints object = storageAccount.properties.primaryEndpoints
