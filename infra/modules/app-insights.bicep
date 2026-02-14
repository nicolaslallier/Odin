@description('Name of the Application Insights component')
param name string

@description('Azure region')
param location string = resourceGroup().location

@description('Log Analytics workspace resource ID (workspace-based App Insights)')
param workspaceResourceId string

@description('Resource tags')
param tags object = {}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspaceResourceId
  }
}

output id string = appInsights.id
output name string = appInsights.name
output instrumentationKey string = appInsights.properties.InstrumentationKey
output connectionString string = appInsights.properties.ConnectionString
