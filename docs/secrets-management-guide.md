# Secrets Management Guide

This guide explains the secrets management system for the InGest-LLM project, including Bitwarden integration, environment configuration, and security best practices.

## Table of Contents

- [Overview](#overview)
- [Bitwarden Secrets Manager Integration](#bitwarden-secrets-manager-integration)
- [Environment Configuration](#environment-configuration)
- [Development Environment Setup](#development-environment-setup)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The InGest-LLM project implements a comprehensive secrets management system with the following key features:

- **Bitwarden Secrets Manager Integration**: Secure storage and retrieval of secrets at runtime
- **Zero Trust Security Mode**: Enforces that no plain-text secrets exist when Bitwarden is enabled
- **Standardized Environment Variables**: All configuration uses `INGEST_` prefix for consistency
- **Pre-Commit Secret Detection**: Automated scanning to prevent secrets from being committed to version control
- **Startup Validation**: Application validates configuration before starting to ensure security compliance

## Bitwarden Secrets Manager Integration

### What is Bitwarden Secrets Manager?

Bitwarden Secrets Manager is a secure secrets management solution that allows you to:
- Store secrets securely in an encrypted vault
- Retrieve secrets programmatically via API
- Rotate secrets without manual intervention
- Audit secret access and usage
- Share secrets securely with team members

### Integration Architecture

The project integrates with Bitwarden Secrets Manager through the following components:

1. **Configuration**: [`src/ingest_llm_as/config.py`](../src/ingest_llm_as/config.py)
   - `INGEST_BWS_ACCESS_TOKEN`: Bitwarden Secrets Manager access token
   - `INGEST_ZERO_TRUST_REQUIRED`: Enable/disable zero-trust security mode
   - Secret ID fields: `*_PRD_ID` for each secret

2. **Security Validation**: [`src/ingest_llm_as/security/`](../src/ingest_llm_as/security/)
   - [`validator.py`](../src/ingest_llm_as/security/validator.py): Detects plain-text secrets
   - [`startup_validator.py`](../src/ingest_llm_as/security/startup_validator.py): Validates configuration at startup

3. **Secret Retrieval**: Application fetches secrets from Bitwarden at runtime using secret IDs

### Setting Up Bitwarden Integration

#### 1. Create Bitwarden Secrets Manager Project

1. Log in to [Bitwarden Secrets Manager](https://vault.bitwarden.com/)
2. Navigate to **Secrets Manager** → **New Project**
3. Create a new project with a descriptive name (e.g., "InGest-LLM Production")
4. Select the appropriate organization

#### 2. Add Secrets to Your Project

For each secret required by the application, add it to your Bitwarden project:

**Required Secrets:**
- `INGEST_POSTGRES_DSN_PRD_ID`: PostgreSQL connection string
- `INGEST_LINEAR_WEBHOOK_SECRET_PRD_ID`: Linear webhook secret
- `INGEST_NANOGPT_API_KEY_PRD_ID`: NanoGPT API key
- `INGEST_OPENROUTER_API_KEY_PRD_ID`: OpenRouter API key
- `INGEST_PERPLEXITY_API_KEY_PRD_ID`: Perplexity API key
- `INGEST_GEMINI_API_KEY_PRD_ID`: Gemini API key
- `INGEST_APIDOG_ACCESS_TOKEN_PRD_ID`: Apidog access token
- `INGEST_APIDOG_PROJECT_ID_PRD_ID`: Apidog project ID
- `INGEST_TAVILY_API_KEY_PRD_ID`: Tavily API key
- `INGEST_BRAVE_API_KEY_PRD_ID`: Brave API key
- `INGEST_KAGI_API_KEY_PRD_ID`: Kagi API key
- `INGEST_EXA_API_KEY_PRD_ID`: Exa API key
- `INGEST_GITHUB_API_KEY_PRD_ID`: GitHub API key
- `INGEST_PERPLEXITY_AI_API_KEY_PRD_ID`: Perplexity AI API key
- `INGEST_JINA_AI_API_KEY_PRD_ID`: Jina AI API key
- `INGEST_FIRECRAWL_API_KEY_PRD_ID`: Firecrawl API key
- `INGEST_FIRECRAWL_BASE_URL_PRD_ID`: Firecrawl base URL

**Optional Secrets:**
- `INGEST_OLLAMA_API_KEY_PRD_ID`: Ollama API key (if using external Ollama)
- `INGEST_LANGFUSE_PUBLIC_KEY_PRD_ID`: Langfuse public key (if using Langfuse observability)
- `INGEST_LANGFUSE_SECRET_KEY_PRD_ID`: Langfuse secret key (if using Langfuse observability)

#### 3. Configure Environment Variables

Set the following environment variables in your `.env` file:

```bash
# Bitwarden Secrets Manager Configuration
INGEST_BWS_ACCESS_TOKEN=your_bitwarden_access_token_here
INGEST_ZERO_TRUST_REQUIRED=true

# Secret IDs (these reference secrets stored in Bitwarden)
INGEST_POSTGRES_DSN_PRD_ID=your_postgres_dsn_secret_id
INGEST_LINEAR_WEBHOOK_SECRET_PRD_ID=your_linear_webhook_secret_id
INGEST_NANOGPT_API_KEY_PRD_ID=your_nanogpt_api_key_id
INGEST_OPENROUTER_API_KEY_PRD_ID=your_openrouter_api_key_id
INGEST_PERPLEXITY_API_KEY_PRD_ID=your_perplexity_api_key_id
INGEST_GEMINI_API_KEY_PRD_ID=your_gemini_api_key_id
INGEST_APIDOG_ACCESS_TOKEN_PRD_ID=your_apidog_access_token_id
INGEST_APIDOG_PROJECT_ID_PRD_ID=your_apidog_project_id
INGEST_TAVILY_API_KEY_PRD_ID=your_tavily_api_key_id
INGEST_BRAVE_API_KEY_PRD_ID=your_brave_api_key_id
INGEST_KAGI_API_KEY_PRD_ID=your_kagi_api_key_id
INGEST_EXA_API_KEY_PRD_ID=your_exa_api_key_id
INGEST_GITHUB_API_KEY_PRD_ID=your_github_api_key_id
INGEST_PERPLEXITY_AI_API_KEY_PRD_ID=your_perplexity_ai_api_key_id
INGEST_JINA_AI_API_KEY_PRD_ID=your_jina_ai_api_key_id
INGEST_FIRECRAWL_API_KEY_PRD_ID=your_firecrawl_api_key_id
INGEST_FIRECRAWL_BASE_URL_PRD_ID=your_firecrawl_base_url_id
```

**Important Notes:**
- Replace `your_*_id` with the actual secret IDs from your Bitwarden project
- Never commit actual secret values to version control
- The secret IDs are references, not the actual secrets
- The application will fetch actual secret values from Bitwarden using these IDs

#### 4. Enable Zero Trust Mode

Set `INGEST_ZERO_TRUST_REQUIRED=true` to enable zero-trust security mode. When enabled:
- The application will reject any plain-text secrets in environment variables
- Only Bitwarden-retrieved secrets are allowed
- This prevents accidental commits of credentials

### How It Works

1. **Application Startup**:
   - [`main.py`](../src/ingest_llm_as/main.py) calls [`validate_startup_config()`](../src/ingest_llm_as/security/startup_validator.py)
   - Validation checks for plain-text secrets when `ZERO_TRUST_REQUIRED=true`
   - Raises `SecurityValidationError` in production, logs warning in development

2. **Secret Retrieval**:
   - Application uses [`get_settings()`](../src/ingest_llm_as/config.py) to access configuration
   - Settings class fetches secrets from Bitwarden using secret IDs
   - Secrets are cached in memory for performance

3. **Security Enforcement**:
   - [`validator.py`](../src/ingest_llm_as/security/validator.py) provides validation functions
   - Detects common secret patterns (API keys, passwords, tokens)
   - Validates environment variables against security policies

## Environment Configuration

### Environment Variable Naming Convention

All environment variables in the InGest-LLM project use the `INGEST_` prefix for consistency and to avoid conflicts.

**Naming Pattern:** `INGEST_<SERVICE>_<PARAMETER>`

**Examples:**
- `INGEST_APP_NAME` - Application name
- `INGEST_APP_ENV` - Application environment (development, staging, production)
- `INGEST_POSTGRES_DSN` - PostgreSQL connection string
- `INGEST_LINEAR_WEBHOOK_SECRET` - Linear webhook secret
- `INGEST_OLLAMA_BASE_URL` - Ollama service URL
- `INGEST_MEMOS_BASE_URL` - memOS service URL

### Configuration Files

The project uses the following configuration files:

1. **`.env`**: Local environment configuration (gitignored)
   - Contains actual environment variable values
   - Never committed to version control
   - Referenced by [`config.py`](../src/ingest_llm_as/config.py)

2. **`.env.example`**: Template for environment variables
   - Shows all required variables with `INGEST_` prefix
   - Contains placeholder values (not actual secrets)
   - Committed to version control as reference

3. **`.env.secure_template`**: Bitwarden-only configuration template
   - Shows secret ID fields instead of actual values
   - Contains `INGEST_ZERO_TRUST_REQUIRED=true` by default
   - Committed to version control as reference for secure deployments

### Configuration Loading

The application uses a non-cached settings pattern:

```python
# Always use this function, never import settings directly
from ingest_llm_as.config import get_settings

# Get fresh settings on every access
settings = get_settings()
```

**Why Non-Cached?**
- Prevents stale configuration in long-running processes
- Ensures environment variable changes are picked up immediately
- Supports hot-reloading of configuration without restart

## Development Environment Setup

### Quick Start Guide

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd InGest-LLM.as
```

#### 2. Set Up Python Environment

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# Or using Poetry (recommended for this project)
poetry install
```

#### 3. Configure Environment Variables

**Option A: Using `.env` file (Development)**

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your local values
# Use a text editor or IDE
notepad .env  # Windows
code .env     # VS Code
```

**Option B: Using Bitwarden (Production/Secure)**

```bash
# Copy the secure template
cp .env.secure_template .env

# Edit .env with your Bitwarden secret IDs
# You must have INGEST_BWS_ACCESS_TOKEN set
notepad .env
```

#### 4. Run the Application

```bash
# Development mode
python -m ingest_llm_as.main

# Or using uvicorn directly
uvicorn ingest_llm_as.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. Verify Configuration

```bash
# Check that settings are loaded correctly
python -c "from ingest_llm_as.config import get_settings; print(get_settings().model_dump())"
```

### Testing Your Setup

#### Health Check

```bash
# Test the health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "..."}
```

#### Run Tests

```bash
# Run unit tests (no integration tests required)
pytest -m "not integration"

# Run all tests (requires memOS running)
pytest
```

## Security Best Practices

### 1. Never Commit Secrets

**Rule:** Never commit actual secret values to version control.

**What to Avoid:**
- API keys, tokens, passwords
- Database connection strings
- Private keys (SSH, SSL, etc.)
- OAuth tokens and refresh tokens
- Session cookies and authentication tokens

**What's Safe:**
- Secret IDs (references to Bitwarden)
- Placeholder values in `.env.example`
- Configuration templates
- Documentation and examples

### 2. Use Environment Variables

**Rule:** Always use environment variables for configuration.

**Benefits:**
- Secrets are not hardcoded in source code
- Different configurations for different environments (dev, staging, prod)
- Easy to rotate secrets without code changes
- Supports containerization and cloud deployments

### 3. Enable Zero Trust Mode in Production

**Rule:** Always enable `INGEST_ZERO_TRUST_REQUIRED=true` in production.

**Why:**
- Prevents accidental commits of production secrets
- Enforces Bitwarden-only secret storage
- Provides clear security audit trail
- Fails fast if secrets are accidentally committed

### 4. Use Pre-Commit Hooks

**Rule:** Pre-commit hooks automatically scan for secrets.

**What They Do:**
- Detect common secret patterns in code
- Block commits containing secrets
- Provide clear error messages
- Run before code is pushed to remote

**Available Hooks:**
- `detect-secrets`: Scans for high-entropy strings and known secret patterns
- `gitleaks`: Additional secret detection with comprehensive rules
- `block-env-files`: Prevents `.env` files from being committed

### 5. Rotate Secrets Regularly

**Rule:** Rotate secrets periodically.

**Recommended Rotation Schedule:**
- API keys: Every 90 days
- Database passwords: Every 180 days
- OAuth tokens: Every 30-60 days (based on provider)

**How to Rotate:**
1. Generate new secret in Bitwarden
2. Update application configuration with new secret ID
3. Deploy updated configuration
4. Revoke old secret (if applicable)

### 6. Use Least Privilege

**Rule:** Grant minimum required permissions.

**Principles:**
- Use read-only API keys when possible
- Limit scope of OAuth tokens
- Use service accounts instead of personal accounts
- Regularly audit access permissions

### 7. Audit Secret Access

**Rule:** Monitor and audit secret usage.

**Bitwarden Features:**
- View access logs for each secret
- See which applications are using secrets
- Revoke access when team members leave
- Set up notifications for secret access

## Troubleshooting

### Issue: Application Fails to Start

**Symptom:** Application raises `SecurityValidationError` on startup.

**Possible Causes:**
1. Plain-text secret detected in environment variables
2. `INGEST_ZERO_TRUST_REQUIRED=true` but secrets found in `.env`
3. Invalid Bitwarden access token
4. Bitwarden API unreachable

**Solutions:**

**Check for Plain-Text Secrets:**
```bash
# Review your .env file
grep -E "(password|secret|key|token)" .env

# If found, either:
# 1. Remove the secret and use Bitwarden instead
# 2. Set INGEST_ZERO_TRUST_REQUIRED=false for development
```

**Verify Bitwarden Configuration:**
```bash
# Test your Bitwarden access token
curl -H "Authorization: Bearer $INGEST_BWS_ACCESS_TOKEN" \
  https://api.bitwarden.com/sm/secrets

# Check that secret IDs exist in your project
```

**Check Application Logs:**
```bash
# Look for validation errors in application logs
# The error message will indicate which variable has the issue
```

### Issue: Pre-Commit Hook Blocks Commit

**Symptom:** Pre-commit hook fails with secret detection error.

**Possible Causes:**
1. Actual secret value committed to code
2. False positive in `.secrets.baseline`
3. New secret pattern not in baseline

**Solutions:**

**Review the Detected Secret:**
```bash
# The pre-commit output will show the file and line number
# Review the code and determine if it's actually a secret
```

**Update Baseline if False Positive:**
```bash
# If it's not a real secret, update the baseline
detect-secrets scan --baseline .secrets.baseline --update

# Commit the updated baseline
git add .secrets.baseline
git commit -m "Update baseline for false positive"
```

**Remove the Secret:**
```bash
# If it is a real secret, remove it and use environment variable
# Or add it to Bitwarden and use secret ID
```

### Issue: Secrets Not Loading from Bitwarden

**Symptom:** Application fails to fetch secrets from Bitwarden.

**Possible Causes:**
1. Invalid secret ID in environment variable
2. Secret not found in Bitwarden project
3. Insufficient permissions for Bitwarden access token
4. Bitwarden API rate limiting or downtime

**Solutions:**

**Verify Secret ID:**
```bash
# Check the secret ID in your .env file
grep INEST_POSTGRES_DSN_PRD_ID .env

# Log in to Bitwarden and verify the secret exists
# Navigate to Secrets Manager → Your Project → Secrets
# Search for the secret ID
```

**Check Bitwarden Access Token:**
```bash
# Verify your access token is valid
echo $INGEST_BWS_ACCESS_TOKEN

# Test API access
curl -H "Authorization: Bearer $INGEST_BWS_ACCESS_TOKEN" \
  https://api.bitwarden.com/sm/secrets
```

**Enable Debug Logging:**
```bash
# Set debug logging to see detailed error messages
export INGEST_LOG_LEVEL=DEBUG

# Run the application
python -m ingest_llm_as.main
```

### Issue: Tests Fail After Configuration Changes

**Symptom:** Tests fail after updating environment variables.

**Possible Causes:**
1. Environment variable name changed but code still uses old name
2. Variable value format changed (e.g., URL encoding)
3. Missing required environment variable

**Solutions:**

**Check Variable Names:**
```bash
# Verify all variables use INGEST_ prefix
grep -r "INGEST_" .env

# Check code for old variable names
grep -r "POSTGRES_DSN\|LINEAR_WEBHOOK_SECRET" src/
```

**Update Code References:**
```bash
# Update code to use new variable names
# Use find and sed for bulk updates
find src/ -name "*.py" -exec sed -i 's/POSTGRES_DSN/INGEST_POSTGRES_DSN/g' {} \;
```

**Run Tests Again:**
```bash
# Clear any cached test data
pytest --cache-clear

# Run tests
pytest -m "not integration"
```

### Issue: Git Ignore Not Working

**Symptom:** File that should be ignored is being tracked by Git.

**Possible Causes:**
1. File not in `.gitignore`
2. `.gitignore` has incorrect pattern
3. File was committed before being added to `.gitignore`

**Solutions:**

**Check Git Status:**
```bash
# See what files are tracked
git status

# Check if the file is in .gitignore
grep filename .gitignore
```

**Remove from Git:**
```bash
# Remove the file from Git tracking
git rm --cached filename

# Commit the removal
git commit -m "Remove sensitive file from tracking"
```

**Update .gitignore:**
```bash
# Add the file pattern to .gitignore
echo "filename" >> .gitignore

# Commit the update
git add .gitignore
git commit -m "Update gitignore"
```

## Additional Resources

### Documentation

- [Environment Variables Reference](environment-variables-reference.md)
- [Operational Runbook](operational-runbook.md)
- [API Endpoints](../api_ingestion_endpoints.md)

### Security Tools

- [Bitwarden Secrets Manager](https://bitwarden.com/products/secrets-manager)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Git Secrets Scanning](https://github.com/trufflesecurity/truffleHog)

### Project Files

- Configuration: [`src/ingest_llm_as/config.py`](../src/ingest_llm_as/config.py)
- Security Validation: [`src/ingest_llm_as/security/`](../src/ingest_llm_as/security/)
- Main Application: [`src/ingest_llm_as/main.py`](../src/ingest_llm_as/main.py)

## Support

For questions or issues related to secrets management:

1. **Bitwarden Issues**: Check [Bitwarden Status](https://status.bitwarden.com/)
2. **Application Issues**: Check application logs and health endpoints
3. **Security Concerns**: Report security vulnerabilities through proper channels

## Summary

The InGest-LLM project implements a robust secrets management system that:

- ✅ Uses Bitwarden Secrets Manager for secure secret storage
- ✅ Enforces zero-trust security mode in production
- ✅ Standardizes environment variables with `INGEST_` prefix
- ✅ Validates configuration at startup
- ✅ Prevents secret commits via pre-commit hooks
- ✅ Provides clear documentation and troubleshooting guides

By following this guide and using the provided security features, you can ensure that secrets are managed securely and never accidentally committed to version control.
