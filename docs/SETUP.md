# POC Setup Instructions

Complete step-by-step guide to set up the Intelligent API Test-Result Analysis POC.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Datadog Configuration](#datadog-configuration)
4. [Ollama Setup](#ollama-setup)
5. [Running Tests](#running-tests)
6. [Verification](#verification)

## Prerequisites

### Required Software

- Python 3.9 or higher
- Docker and Docker Compose (for Ollama)
- Git
- k6 (optional, for local testing)

### System Requirements

- 2+ GB RAM (for analysis engine)
- 4+ GB RAM (if running Ollama locally)
- 5+ GB disk space
- Internet connection (for initial setup)

### Accounts

- Datadog account (free trial acceptable)
- GitHub account (for Actions - optional)

## Environment Setup

### 1. Clone or Create Project

```bash
cd /path/to/POC
# Structure already created
```

### 2. Install Python Dependencies

```bash
cd python
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Create .env File

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Your values here
DATADOG_API_KEY=your_actual_api_key
DATADOG_APP_KEY=your_actual_app_key
DATADOG_SITE=datadoghq.com
```

## Datadog Configuration

### Getting API Keys

1. **Sign up for Datadog** (free trial)
   - Go to https://www.datadoghq.com/free-datadog-trial/
   - Complete sign-up

2. **Get API Key**
   - Log into Datadog
   - Go to Settings → API Keys
   - Copy/generate a new API key
   - Paste into `.env` as `DATADOG_API_KEY`

3. **Get Application Key**
   - In Datadog, go to Settings → Application Keys
   - Create new application key
   - Copy and paste into `.env` as `DATADOG_APP_KEY`

### Verify Connection

```bash
cd python
python -c "
from modules.datadog.datadog_client import DatadogClient
from config import DATADOG_API_KEY, DATADOG_APP_KEY

client = DatadogClient(DATADOG_API_KEY, DATADOG_APP_KEY)
if client.health_check():
    print('✓ Datadog connection successful!')
else:
    print('✗ Datadog connection failed')
"
```

## Ollama Setup

### 1. Start Ollama Container

```bash
cd docker
docker-compose up -d
```

### 2. Verify Container is Running

```bash
docker ps | grep ollama
```

You should see `api_test_analysis_ollama` container running.

### 3. Pull a Model

Choose and download one of these models:

**Gemma 2B (Fast, ~1GB) - Recommended for POC**
```bash
docker exec api_test_analysis_ollama ollama pull gemma:2b
```

**Or Gemma 7B (Better quality, ~4GB)**
```bash
docker exec api_test_analysis_ollama ollama pull gemma:7b
```

Wait for download to complete. You'll see:
```
pulling manifest
pulling ...
done
```

### 4. Verify Model is Available

```bash
curl http://localhost:11434/api/tags
```

You should see your downloaded model listed.

### 5. Update .env

In `python/.env`, set the model name:

```
OLLAMA_MODEL=gemma:2b
OLLAMA_API_URL=http://localhost:11434
```

### 6. Test Ollama Connection

```bash
cd python
python -c "
from modules.ai.ollama_client import OllamaClient

client = OllamaClient()
if client.health_check():
    print('✓ Ollama connection successful!')
else:
    print('✗ Ollama connection failed')
"
```

## Jira Cloud Configuration

### Option A: Use Real Jira Cloud (Recommended)

This integration uses real Jira Cloud API for automatic issue correlation. Perfect for personal/free tier accounts.

**See [JIRA_CLOUD_SETUP.md](JIRA_CLOUD_SETUP.md) for complete setup instructions.**

Quick setup:
1. Create free Jira Cloud account at https://www.atlassian.com
2. Create API token (Settings → API Tokens)
3. Add to `.env`:
   ```
   JIRA_API_URL=https://yourname.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your_token_here
   JIRA_PROJECT_KEY=PROJ
   ```
4. Test connection:
   ```bash
   cd python
   python -c "from modules.jira.jira_client import JiraClient; print('✓ Connected!' if JiraClient().health_check() else '✗ Failed!')"
   ```

### Option B: Skip Jira (Optional)

Leave Jira credentials empty in `.env` - system will still work with limited correlation.

## Running Tests

### k6 Tests Organization

k6 tests are organized by service:
- `k6/tests/customer_service.js` - Customer API tests (4 tests)
- `k6/tests/order_service.js` - Order API tests (4 tests)
- `k6/tests/payment_service.js` - Payment API tests (4 tests)

Each service can be run independently or all together.

### Option 1: With Sample Data (Recommended for First Run)

```bash
cd python
python main.py --k6-result ../k6/sample_results.json --dry-run
```

This runs with sample data without sending to Datadog. Perfect for verification.

### Option 2: Run Individual Service Tests

**Customer Service Tests:**
```bash
cd k6
k6 run tests/customer_service.js --out json=results_customer.json
```

**Order Service Tests:**
```bash
k6 run tests/order_service.js --out json=results_order.json
```

**Payment Service Tests:**
```bash
k6 run tests/payment_service.js --out json=results_payment.json
```

### Option 3: Run All Service Tests

```bash
cd k6
k6 run tests/customer_service.js tests/order_service.js tests/payment_service.js --out json=results.json
```

Then run analysis:

```bash
cd ../python
python main.py --k6-result ../k6/results.json
```

### Option 4: Dry-Run Mode (No Datadog Upload)

```bash
cd python
DRY_RUN=true python main.py --k6-result ../k6/sample_results.json
```

This shows what would be sent to Datadog without actually sending it.

## Verification

### 1. Check Analysis Engine

Run sample analysis:

```bash
cd python
python main.py --k6-result ../k6/sample_results.json --dry-run
```

Expected output:
- ✓ Parsing k6 results
- ✓ Ingesting into Datadog (or [DRY RUN])
- ✓ Querying historical data
- ✓ Classifying failures
- ✓ Correlating with Jira
- ✓ AI analysis (if Ollama available)
- ✓ Summary generation

### 2. Check Log Files

```bash
ls -la python/logs/
cat python/logs/analysis.log
```

Should contain debug information from the run.

### 3. Verify in Datadog (if not dry-run)

1. Go to https://app.datadoghq.com (or your Datadog site)
2. Check **Events** → Should see test execution events
3. Check **Metrics** → Look for `test.*` metrics
4. Create dashboard to visualize results

### 4. Quick Sanity Checks

**K6 works:**
```bash
k6 version
```

**Python 3.9+:**
```bash
python --version
```

**Docker running:**
```bash
docker ps
```

**Ollama accessible:**
```bash
curl http://localhost:11434/api/tags
```

## Common Issues & Solutions

### Issue: "ImportError: No module named 'modules'"

**Solution:**
```bash
cd python
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python main.py --k6-result ../k6/sample_results.json --dry-run
```

### Issue: "Datadog API key not set"

**Solution:**
```bash
# Edit python/.env
DATADOG_API_KEY=your_real_key_here
```

Or set environment variable:
```bash
export DATADOG_API_KEY=your_key_here
```

### Issue: "Ollama connection failed"

**Solution:**
```bash
# Check if container is running
docker ps | grep ollama

# If not running, start it
cd docker
docker-compose up -d

# Check logs
docker logs api_test_analysis_ollama

# Verify port is accessible
curl http://localhost:11434/api/tags
```

### Issue: "DRY RUN mode enabled"

**Solution:**
DRY_RUN is enabled by default or in .env. To send real data to Datadog:

```bash
# Edit python/.env
DRY_RUN=False

# Or use environment variable
DRY_RUN=False python main.py --k6-result ../k6/results.json
```

### Issue: Out of Memory

**Solution:**
- Reduce Ollama resource limits in `docker/docker-compose.yml`
- Use smaller model: `gemma:2b` instead of `gemma:7b`
- Ensure no other heavy processes are running

### Issue: K6 Tests Timeout

**Solution:**
```bash
# Increase timeout
k6 run tests/api_tests.js --out json=results.json --timeout 60s

# Or run with fewer VUs
K6_VUS=1 k6 run tests/api_tests.js --out json=results.json
```

## Next Steps

1. **Explore Results**: Check `python/logs/analysis.log` for detailed output
2. **Create Dashboard**: In Datadog, create a custom dashboard with metrics
3. **Customize Classification**: Edit `python/modules/analysis/classification_rules.py`
4. **Add Tests**: Add more k6 test services in `k6/tests/`
5. **Generate Historical Data**: Use mock data to simulate 10-day history

## Getting Help

1. Check logs: `python/logs/analysis.log`
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for design details
3. Check individual module docstrings in `python/modules/`

---

**Setup Complete!** You're ready to run the API Test Analysis POC.
