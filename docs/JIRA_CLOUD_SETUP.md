# Jira Cloud Integration Setup Guide

This guide walks you through setting up real Jira Cloud API integration for the POC system.

## Prerequisites

- Personal Jira Cloud account (free tier available)
- Atlassian account with access to Jira
- Python 3.9+

## Step 1: Create/Access Your Jira Cloud Instance

1. Go to [atlassian.com](https://www.atlassian.com)
2. Sign up for a free Jira Cloud account if you don't have one
3. Create a new project or use an existing one
4. Note your instance URL: `https://yourname.atlassian.net`

## Step 2: Create Jira API Token

1. Go to [account.atlassian.com/manage-profile/security/api-tokens](https://account.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API Token"
3. Give it a name (e.g., "POC Analysis Engine")
4. Click "Create"
5. Copy the generated token (you'll only see it once!)

## Step 3: Configure Environment Variables

Edit `python/.env` with your Jira credentials:

```bash
# Jira Configuration (Real Jira Cloud API)
JIRA_API_URL=https://yourname.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_api_token_here
JIRA_PROJECT_KEY=PROJ
```

### Configuration Details:

- **JIRA_API_URL**: Your Jira instance URL (e.g., `https://mycompany.atlassian.net`)
- **JIRA_EMAIL**: Email address associated with your Jira account
- **JIRA_API_TOKEN**: API token created in Step 2
- **JIRA_PROJECT_KEY**: The key for your Jira project (e.g., `PROJ`, `TEST`, `BUG`)

To find your project key:
1. Go to your Jira instance
2. Navigate to Project Settings → General
3. Look for "Project key" field (uppercase, e.g., `PROJ`)

## Step 4: Create Jira Project (Optional)

If you don't have a project yet:

1. In your Jira instance, click "Create" → "Project"
2. Choose "Software" project template
3. Select "Kanban" or "Scrum"
4. Name it (e.g., "API Test Analysis")
5. Note the project key

## Step 5: Verify Configuration

Run the health check:

```bash
cd python
python -c "from modules.jira.jira_client import JiraClient; client = JiraClient(); print('Connected!' if client.health_check() else 'Failed!')"
```

Expected output:
```
2024-01-15 10:30:45 [jira.client] INFO - Connected to Jira as: Your Name
```

## Step 6: Create Sample Issues (Optional)

You can pre-populate Jira with sample issues for correlation testing:

1. Go to your Jira project
2. Click "Create" → "Create Issue"
3. Add issues related to your services:
   - **Summary**: "Customer/CreateCustomer - API Timeout"
   - **Issue Type**: Bug
   - **Labels**: test-automation, api-test, customer
   
4. Add more issues for other services (Order, Payment)

Or use the API:

```python
from modules.jira.jira_client import JiraClient

client = JiraClient()
issue_key = client.create_issue(
    project_key='PROJ',
    summary='Customer/CreateCustomer - Persistent timeout',
    description='API tests consistently timing out when creating customers',
    issue_type='Bug',
    labels=['test-automation', 'api-test', 'customer']
)
print(f"Created issue: {issue_key}")
```

## How It Works

### Issue Correlation

When a test failure is detected, the system:

1. **Searches for matching Jira issues** using the service name and test name
2. **Ranks results** by relevance
3. **Returns correlation details** if a match is found
4. **Optionally creates a new issue** if configured

### Search Strategy

The correlation system searches for:
- Service name in issue summary
- Test name in issue summary
- Failure category (if available)

Example query:
```
project = PROJ AND summary ~ "customer" AND summary ~ "create"
```

### Creating Issues Automatically

Set in the pipeline to auto-create Jira issues for new recurring failures:

```python
result = jira_correlation.correlate_failure(
    service='Customer',
    test='CreateCustomer',
    failure_pattern='Persistent Failure',
    create_if_missing=True
)
```

## Troubleshooting

### "Jira authentication failed"
- Verify your email is correct
- Regenerate API token (old token may have expired)
- Check token is not truncated in .env file

### "No such project found"
- Verify JIRA_PROJECT_KEY in config
- Ensure you have access to the project
- Project key is case-sensitive

### "Connection timeout"
- Verify JIRA_API_URL is correct (no trailing slash)
- Check internet connectivity
- Verify Jira instance is accessible

### Health check passes but correlation fails
- Verify you have permission to search issues
- Check issues exist in your Jira project
- Increase log level to DEBUG for more details

## API Reference

### JiraClient Methods

```python
# Initialize
client = JiraClient(
    jira_url='https://instance.atlassian.net',
    email='user@example.com',
    api_token='token'
)

# Health check
client.health_check()  # Returns True/False

# Search issues
issues = client.search_issues('project = PROJ AND status = Open')

# Find by summary
issue = client.find_issue_by_summary('PROJ', ['customer', 'create'])

# Find by label
issue = client.find_issue_by_label('PROJ', 'api-test')

# Create issue
key = client.create_issue(
    project_key='PROJ',
    summary='Issue title',
    description='Issue description',
    labels=['tag1', 'tag2']
)

# Update issue
client.update_issue('PROJ-123', summary='New title')

# Get issue
issue = client.get_issue('PROJ-123')
```

## Security Notes

- API tokens grant access to your Jira instance
- Store tokens securely in `.env` files (never commit to Git)
- Regenerate tokens periodically
- Use read-only account for POC if possible

## Free Tier Limitations

Jira Cloud free tier includes:
- Up to 10 users
- Unlimited storage
- Unlimited issues
- Full API access
- No custom fields for free tier

Perfect for POC testing!

## Next Steps

1. Configure credentials in `.env`
2. Run health check
3. Create sample Jira issues
4. Run analysis pipeline with real Jira enabled
5. Verify correlation matches your issues

## References

- [Jira Cloud API Documentation](https://developer.atlassian.com/cloud/jira/rest/v3/)
- [Create API Token](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [Jira Query Language (JQL)](https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql/)
