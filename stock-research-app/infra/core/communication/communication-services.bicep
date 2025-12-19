// Azure Communication Services module
param name string
param location string = 'global'
param tags object = {}
param emailServiceName string
param emailDomain string = ''

resource communicationService 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    dataLocation: 'United States'
  }
}

resource emailService 'Microsoft.Communication/emailServices@2023-04-01' = if (!empty(emailDomain)) {
  name: emailServiceName
  location: location
  tags: tags
  properties: {
    dataLocation: 'United States'
  }
}

resource emailDomainResource 'Microsoft.Communication/emailServices/domains@2023-04-01' = if (!empty(emailDomain)) {
  parent: emailService
  name: emailDomain
  location: location
  tags: tags
  properties: {
    domainManagement: 'CustomerManaged'
  }
}

output name string = communicationService.name
output connectionString string = communicationService.listKeys().primaryConnectionString
output emailServiceName string = emailService.name
