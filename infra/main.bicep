@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Naming prefix (e.g. odin-dev, odin-prod)')
param namePrefix string

@description('Resource tags')
param tags object = {}

var logAnalyticsName = '${replace(namePrefix, '-', '')}-logs'
var appInsightsName = '${replace(namePrefix, '-', '')}-ai'
var keyVaultName = '${replace(namePrefix, '-', '')}kv'
var storageName = '${replace(namePrefix, '-', '')}st'
var containerAppsEnvName = '${replace(namePrefix, '-', '')}-cae'

module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'logAnalytics'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
  }
}

module appInsights 'modules/app-insights.bicep' = {
  name: 'appInsights'
  params: {
    name: appInsightsName
    location: location
    workspaceResourceId: logAnalytics.outputs.id
    tags: tags
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVault'
  params: {
    name: keyVaultName
    location: location
    tags: tags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: storageName
    location: location
    tags: tags
  }
}

module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv'
  params: {
    name: containerAppsEnvName
    location: location
    logAnalyticsWorkspaceId: logAnalytics.outputs.id
    tags: tags
  }
}

output keyVaultName string = keyVault.outputs.name
output keyVaultUri string = keyVault.outputs.vaultUri
output storageAccountName string = storage.outputs.name
output appInsightsConnectionString string = appInsights.outputs.connectionString
output appInsightsInstrumentationKey string = appInsights.outputs.instrumentationKey
output containerAppsEnvironmentId string = containerAppsEnv.outputs.id
output logAnalyticsWorkspaceId string = logAnalytics.outputs.id
