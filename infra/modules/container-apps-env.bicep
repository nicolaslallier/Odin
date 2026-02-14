@description('Name of the Container Apps environment')
param name string

@description('Azure region')
param location string = resourceGroup().location

@description('Log Analytics workspace ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Resource tags')
param tags object = {}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').properties.customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2020-08-01').primarySharedKey
      }
    }
  }
}

output id string = containerAppsEnv.id
output name string = containerAppsEnv.name
