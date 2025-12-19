# .azure directory

This directory is used by Azure Developer CLI (azd) to store environment-specific configuration and state.

## Contents

- Environment configurations are stored here after running `azd init` or `azd env new`
- Each environment has its own subdirectory with configuration files
- These files contain environment-specific values and deployment state

## Important Notes

- **Do not commit** environment files to source control if they contain sensitive information
- The `.gitignore` should exclude `.azure/*/.env` and similar files
- You can have multiple environments (e.g., dev, staging, prod) each with their own configuration

## Example Environment Structure

After running `azd init`, you'll see:

```
.azure/
  └── <environment-name>/
      ├── .env
      └── config.json
```

## Getting Started

1. Initialize your environment:
   ```bash
   azd init
   ```

2. Or create a new environment:
   ```bash
   azd env new <environment-name>
   ```

3. Set environment variables:
   ```bash
   azd env set AZURE_LOCATION eastus
   azd env set EMAIL_SENDER_ADDRESS noreply@example.com
   ```

4. View environment configuration:
   ```bash
   azd env get-values
   ```
