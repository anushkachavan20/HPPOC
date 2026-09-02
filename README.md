# Intelligent API Test-Result Analysis POC

A proof-of-concept system for analyzing API test results at Service/Test level with historical comparison, failure pattern detection, Jira correlation, and AI-powered failure reason analysis.

## Overview

This POC demonstrates an end-to-end system that:

1. Executes k6 API tests via GitHub Actions
2. Ingests results into Datadog (source of truth)
3. Performs deterministic historical analysis (previous 10 executions)
4. Classifies failure patterns (Healthy/New/Persistent/Flaky/Resolved)
5. Correlates failures with Jira issues (mock dataset)
6. Uses Ollama + local LLM to detect failure reasons (failed tests only)
7. Publishes comprehensive analysis to Datadog dashboard

## Architecture

```
GitHub Actions → k6 Tests → Datadog → Python Analysis Engine → Datadog Dashboard
```

The core analysis layer is modular and can be easily adapted to accept results from Testway or other test platforms.

## Tech Stack

- **GitHub Actions**: CI/CD execution (temporary Testway substitute)
- **k6**: API test framework (organized by service)
- **Python 3.9+**: Analysis orchestration engine
- **Datadog**: Metrics, logs, events, dashboards (source of truth)
- **Ollama + Gemma 2/Mistral**: Local LLM for failure analysis
- **Docker**: Local Ollama runtime
- **Jira Cloud**: Real Jira API integration for issue correlation

## Quick Start

### Prerequisites

1. Python 3.9+
2. Datadog account (free trial available)
3. Docker (for Ollama)
4. GitHub account with Actions enabled

### Setup

1. **Clone/Create the project**
   ```bash
   cd /path/to/poc
   ```

2. **Install dependencies**
   ```bash
   cd python
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Datadog API keys
   ```

4. **Start Ollama locally** (Docker)
   ```bash
   cd docker
   docker-compose up -d
   # Wait for Ollama to be ready
   # Then pull a model: docker exec ollama ollama pull gemma:7b
   ```

5. **Run analysis**
   ```bash
   cd python
   python main.py --k6-result ../k6/results.json
   ```

## Project Structure

```
poc/
├── .github/workflows/          # GitHub Actions workflows
├── k6/                         # k6 test scripts
├── python/                     # Analysis engine
│   ├── modules/               # Core analysis modules
│   ├── main.py               # Entry point
│   ├── requirements.txt       # Dependencies
│   └── .env.example          # Config template
├── datadog/                    # Dashboard definitions
├── mock_data/                  # Mock Jira dataset
├── docker/                     # Ollama setup
└── docs/                       # Documentation
```

## Key Features

### 1. Historical Analysis
- Queries Datadog for previous 10 executions
- Calculates pass/fail metrics
- Deterministic (no AI involved)

### 2. Failure Pattern Classification
- **Healthy**: Currently passing, minimal recent failures
- **New Failure**: Was passing, now failing
- **Persistent Failure**: 70%+ failures in last 10 executions
- **Flaky Failure**: Alternating PASS/FAIL pattern
- **Resolved Failure**: Previously failing, now passing

Thresholds are configurable in `python/modules/analysis/classification_rules.py`

### 3. Jira Correlation
- Matches recurring failures against mock Jira dataset
- Returns Jira ID and status if found
- Recommends creating Jira issue if no match found
- Does NOT automatically create issues

### 4. AI Failure Analysis
- **Only for failed tests**
- Uses local Ollama + small LLM (Gemma 2 or Mistral 7B)
- Analyzes error messages, logs, and response information
- Returns structured output:
  ```json
  {
    "failure_reason": "Database connection pool exhausted",
    "failure_category": "Database",
    "evidence": "Multiple connection timeout errors in logs",
    "confidence": "High"
  }
  ```
- Never invents information; returns "Unknown/Insufficient evidence" when needed

### 5. Datadog Dashboard
- Service/Test level metrics
- Historical patterns (10-day comparison)
- AI failure reasons
- Jira correlation
- Filterable by environment, service, test, status

## Configuration

All configuration is in environment variables (`.env` file). See `.env.example` for template:

```
DATADOG_API_KEY=your_api_key
DATADOG_APP_KEY=your_app_key
DATADOG_SITE=datadoghq.com

OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=gemma:7b

JIRA_MOCK_FILE=../mock_data/mock_jira.json
```

## Running the POC

### Full Flow

```bash
# 1. Trigger k6 tests (via GitHub Actions or manually)
cd k6
k6 run tests/customer_service.js

# 2. Run analysis engine
cd ../python
python main.py --k6-result ../k6/results.json

# 3. View results in Datadog dashboard
# Open: https://datadoghq.com (or your Datadog site)
```

### Manual Execution

```bash
python main.py \
  --k6-result ./sample_k6_result.json \
  --execution-id gh_run_12345 \
  --dry-run  # Don't send to Datadog
```

## Example Output

```
=== API Test Analysis Summary ===
Total Tests: 10
Passed: 7 (70%)
Failed: 3 (30%)

Failure Breakdown:
- Persistent: 2 (8/10 failures)
- Flaky: 1 (4/10 failures)
- New: 0

Jira Coverage: 1 existing issue (PROJ-101), 1 needs investigation

Analysis Complete. Results published to Datadog.
```

## Development

### Add New Test Services

1. Create new k6 script in `k6/tests/`
2. Follow naming: `service_name.js`
3. Ensure output matches expected format
4. Add to GitHub Actions workflow

### Customize Failure Classifications

Edit `python/modules/analysis/classification_rules.py`:

```python
FAILURE_THRESHOLDS = {
    'persistent_threshold': 0.70,  # 70% failures
    'flaky_window': 10,             # Last 10 executions
    'new_failure_lookback': 5       # Check last 5 for baseline
}
```

### Integrate with Real Jira

Replace `modules/jira/mock_jira.json` with real Jira API calls in `modules/jira/jira_client.py`. The interface is designed to be swappable.

### Replace GitHub Actions with Testway

1. Update `ingestion/k6_result_parser.py` to accept Testway result format
2. Adjust tags/metadata as needed
3. Core analysis logic remains unchanged

## Datadog Setup

### Required Permissions

- Metrics (read/write)
- Events (read/write)
- Logs (read/write)
- Dashboard (create/modify)

### Data Ingested to Datadog

1. **Events**: Each test execution
2. **Metrics**: Pass/fail counts, duration, patterns
3. **Logs**: Detailed k6 logs and error messages
4. **Custom Metadata**: AI analysis, Jira correlation, failure patterns

All tagged with:
- `environment:poc`
- `service:*service_name*`
- `test:*test_name*`

## Limitations & Assumptions

1. **Datadog Free Tier**: Limited retention (~15 days). POC data will expire.
2. **Ollama Local Only**: LLM runs locally; no cloud API costs.
3. **Mock Jira**: Real Jira integration not included but designed to be swappable.
4. **Historical Seeding**: Mock historical data for demonstration; adjust as needed.
5. **API Rate Limits**: No specific handling for Datadog rate limits; add if needed.

## Next Steps (Beyond POC)

1. Replace mock Jira with real Jira API integration
2. Replace GitHub Actions trigger with Testway integration
3. Add persistent local database for audit trail (optional)
4. Enhance Ollama model selection and fine-tuning
5. Add webhook notifications for critical failures
6. Implement result trending and anomaly detection

## Support

For questions or issues, refer to:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Technical architecture
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) - Datadog data model
- [docs/SETUP.md](docs/SETUP.md) - Detailed setup instructions
- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) - Implementation details

---

**Status**: Proof of Concept (POC)  
**Last Updated**: 2026-09-01
