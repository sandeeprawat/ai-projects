// Module for assigning Cosmos DB role to managed identity
// Deployed to the resource group containing the Cosmos DB account

param cosmosDbAccountName string
param principalId string

// Reference to existing Cosmos DB account
resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: cosmosDbAccountName
}

// Cosmos DB Built-in Data Contributor role (read/write) for the managed identity
// Role Definition ID: 00000000-0000-0000-0000-000000000002 is the built-in "Cosmos DB Built-in Data Contributor"
resource cosmosDataContributorRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-04-15' = {
  name: guid(cosmosDb.id, principalId, '00000000-0000-0000-0000-000000000002')
  parent: cosmosDb
  properties: {
    roleDefinitionId: '${cosmosDb.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: principalId
    scope: cosmosDb.id
  }
}
