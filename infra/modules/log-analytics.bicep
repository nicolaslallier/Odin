@description('Name of the Log Analytics workspace')
param name string

@description('Azure region for the workspace')
param location string = resourceGroup().location

@description('SKU name: PerGB2018, Free, or CapacityReservation')
param sku string = 'PerGB2018'

@description('Retention in days (30-730)')
param retentionInDays int = 30

@description('Resource tags')
param tags object = {}

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: sku
    }
    retentionInDays: retentionInDays
  }
}

output id string = workspace.id
output name string = workspace.name
output customerId string = workspace.properties.customerId
