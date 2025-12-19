# Post-Deployment Configuration Checklist

After deploying the Stock Research Application to Azure, follow this checklist to complete the setup.

## ✅ Immediate Post-Deployment Tasks

### 1. Configure Azure Communication Services Email

- [ ] Navigate to Azure Portal → Communication Services
- [ ] Go to Email → Domains
- [ ] Choose one:
  - **Option A (Quick Start):** Use Azure-managed domain (AzureManagedDomain)
  - **Option B (Custom Domain):** Add your own domain and verify DNS
- [ ] Note the sender email address
- [ ] Update Function App settings:
  ```bash
  az functionapp config appsettings set \
    --name <function-app-name> \
    --resource-group <resource-group-name> \
    --settings EMAIL_SENDER=<sender-email-address>
  ```

### 2. Configure Static Web App Authentication

- [ ] Navigate to Azure Portal → Static Web App
- [ ] Go to Settings → Authentication
- [ ] Add Microsoft (Azure AD) provider:
  - [ ] Click "Add" → Select "Microsoft"
  - [ ] Configure app registration or create new
  - [ ] Set redirect URLs
  - [ ] Save configuration
- [ ] Add Google provider:
  - [ ] Click "Add" → Select "Google"
  - [ ] Enter Google OAuth client ID and secret
  - [ ] Set redirect URLs
  - [ ] Save configuration
- [ ] Test authentication by accessing the web app

### 3. Verify Environment Variables

- [ ] Check Function App configuration:
  ```bash
  az functionapp config appsettings list \
    --name <function-app-name> \
    --resource-group <resource-group-name>
  ```
- [ ] Verify these settings exist:
  - [ ] AZURE_OPENAI_ENDPOINT
  - [ ] AZURE_OPENAI_DEPLOYMENT
  - [ ] BING_V7_ENDPOINT
  - [ ] COSMOS_DB_URL
  - [ ] COSMOS_DB_NAME
  - [ ] REPORTS_CONTAINER
  - [ ] ACS_CONNECTION_STRING
  - [ ] EMAIL_SENDER
  - [ ] APP_BASE_URL

### 4. Test Basic Functionality

- [ ] Access the Static Web App URL
- [ ] Log in with Microsoft or Google account
- [ ] Verify the dashboard loads
- [ ] Try creating a test schedule
- [ ] Run a test research report
- [ ] Check that the report is generated and stored

## 🔒 Security Configuration

### 5. Review Access Controls

- [ ] Verify Function App Managed Identity has appropriate roles:
  - [ ] Cosmos DB Built-in Data Contributor
  - [ ] Storage Blob Data Contributor
  - [ ] Key Vault Secrets User
- [ ] Check Key Vault access policies
- [ ] Review RBAC assignments in resource group

### 6. Configure CORS (if needed)

- [ ] If web app is on custom domain, update CORS in Function App:
  ```bash
  az functionapp cors add \
    --name <function-app-name> \
    --resource-group <resource-group-name> \
    --allowed-origins https://yourdomain.com
  ```

### 7. Enable Advanced Security Features

- [ ] Enable Microsoft Defender for Cloud (optional)
- [ ] Configure Azure Front Door or Application Gateway (optional)
- [ ] Set up Azure DDoS Protection (for production)
- [ ] Enable diagnostic settings for all resources

## 📊 Monitoring Setup

### 8. Configure Application Insights

- [ ] Navigate to Application Insights resource
- [ ] Review Live Metrics Stream
- [ ] Set up Smart Detection alerts
- [ ] Configure availability tests:
  - [ ] Create ping test for web app
  - [ ] Create ping test for API health endpoint

### 9. Set Up Alerts

- [ ] Create alert for Function App errors:
  ```bash
  az monitor metrics alert create \
    --name function-errors \
    --resource-group <resource-group-name> \
    --scopes <function-app-resource-id> \
    --condition "avg exceptions/server > 5" \
    --description "Function App has high error rate"
  ```
- [ ] Create alert for Cosmos DB RU consumption
- [ ] Create alert for Storage quota
- [ ] Create budget alert for cost management

### 10. Enable Logging

- [ ] Configure Log Analytics workspace retention
- [ ] Enable diagnostic logs for:
  - [ ] Function App
  - [ ] Static Web App
  - [ ] Cosmos DB
  - [ ] Storage Account
- [ ] Create log queries for common scenarios

## 🔧 Optional Enhancements

### 11. Custom Domain Setup (Optional)

For Static Web App:
- [ ] Purchase or use existing domain
- [ ] Navigate to Static Web App → Custom domains
- [ ] Add custom domain
- [ ] Configure DNS records (CNAME or TXT)
- [ ] Verify domain
- [ ] Enable HTTPS (automatic with Azure)

For Function App (if using premium plan):
- [ ] Configure custom domain
- [ ] Upload SSL certificate or use managed certificate

### 12. CI/CD Configuration

- [ ] Review GitHub Actions workflow (`.github/workflows/azure-deploy.yml`)
- [ ] Add required secrets to GitHub repository:
  - [ ] AZURE_CLIENT_ID
  - [ ] AZURE_TENANT_ID
  - [ ] AZURE_SUBSCRIPTION_ID
  - [ ] AZURE_LOCATION
- [ ] Test workflow by pushing to main branch
- [ ] Configure branch protection rules

### 13. Performance Optimization

- [ ] Enable Azure CDN for static content (optional)
- [ ] Configure caching policies
- [ ] Review Cosmos DB indexing policy
- [ ] Consider upgrading to Functions Premium plan for production
- [ ] Enable Application Insights sampling if needed

### 14. Backup and Disaster Recovery

- [ ] Enable soft delete for Key Vault (already enabled by default)
- [ ] Configure Cosmos DB backup policy
- [ ] Document recovery procedures
- [ ] Test failover scenarios (if multi-region)
- [ ] Set up Azure Site Recovery (for production)

## 🧪 Testing Checklist

### 15. End-to-End Testing

- [ ] Create a schedule with daily recurrence
- [ ] Trigger manual research run
- [ ] Verify report generation
- [ ] Check email delivery
- [ ] Test report download (Markdown, HTML, PDF)
- [ ] Verify report history
- [ ] Test schedule update
- [ ] Test schedule deletion
- [ ] Verify timer trigger (wait for scheduled time)

### 16. Load Testing (Production Only)

- [ ] Use Azure Load Testing or JMeter
- [ ] Test concurrent users
- [ ] Monitor resource utilization
- [ ] Identify bottlenecks
- [ ] Adjust scaling settings if needed

## 📝 Documentation

### 17. Update Documentation

- [ ] Document custom domain settings
- [ ] Document authentication setup
- [ ] Record resource names and URLs
- [ ] Document any custom configurations
- [ ] Update runbook for operations team

### 18. Create Operational Procedures

- [ ] Document deployment process
- [ ] Create troubleshooting guide
- [ ] Document backup/restore procedures
- [ ] Create incident response plan
- [ ] Document cost optimization strategies

## 💰 Cost Management

### 19. Review and Optimize Costs

- [ ] Review Azure Cost Management dashboard
- [ ] Set up cost alerts
- [ ] Review resource utilization
- [ ] Identify unused resources
- [ ] Consider reserved instances for production
- [ ] Implement auto-shutdown for dev/test environments

### 20. Tagging and Organization

- [ ] Verify all resources have appropriate tags:
  - [ ] Environment (dev/staging/prod)
  - [ ] Cost center
  - [ ] Owner
  - [ ] Project
- [ ] Create Azure Policy for tag enforcement (optional)
- [ ] Review resource organization in resource groups

## 🎓 Training and Handoff

### 21. Team Training

- [ ] Train team on application features
- [ ] Document admin procedures
- [ ] Share monitoring dashboards
- [ ] Conduct deployment walkthrough
- [ ] Share support contact information

### 22. Knowledge Transfer

- [ ] Review architecture with team
- [ ] Explain security model
- [ ] Share access credentials (via Key Vault)
- [ ] Document escalation procedures
- [ ] Schedule regular review meetings

## ✨ Final Verification

### 23. Production Readiness Check

- [ ] All authentication providers working
- [ ] Email delivery configured and tested
- [ ] Monitoring and alerts active
- [ ] Backup procedures documented
- [ ] Cost alerts configured
- [ ] Security review completed
- [ ] Performance testing passed
- [ ] Documentation up to date
- [ ] Team trained and ready
- [ ] Support plan in place

### 24. Go-Live Preparation

- [ ] Schedule go-live time
- [ ] Notify stakeholders
- [ ] Plan communication strategy
- [ ] Prepare rollback plan
- [ ] Have support team on standby
- [ ] Monitor closely after launch

## 📞 Support Contacts

### Azure Support
- **Portal:** https://portal.azure.com → Help + Support
- **Documentation:** https://learn.microsoft.com/azure/

### Application Support
- **GitHub Issues:** [Repository URL]
- **Internal Support:** [Your team contact]

---

## 🎉 Completion

Once all items are checked:
- [ ] Archive this checklist for future reference
- [ ] Schedule first review/retrospective
- [ ] Celebrate successful deployment! 🎊

**Note:** This checklist should be customized based on your organization's specific requirements and policies.
