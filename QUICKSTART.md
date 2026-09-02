# Quick Start Guide

Get the POC running in 5 minutes (with sample data).

## Prerequisites

- Python 3.9+
- 2 GB RAM

## Step 1: Install Dependencies (2 min)

```bash
cd python
pip install -r requirements.txt
```

## Step 2: Configure Environment (1 min)

```bash
cp .env.example .env
# Edit .env if you want real Datadog - leave as is for dry-run
```

## Step 3: Run Analysis (1 min)

```bash
python main.py --k6-result ../k6/sample_results.json --dry-run
```

**Expected Output**:
```
=== API Test Analysis Summary ===
Total Tests Executed: 10
Passed: 7 (70.0%)
Failed: 3 (30.0%)

Failure Breakdown:
  - Persistent Failures: 1
  - Flaky Failures: 1
  - New Failures: 1

Analysis Complete!
```

## Step 4: Check Logs (1 min)

```bash
cat python/logs/analysis.log
```

## Done! 🎉

You've successfully run the API Test Analysis POC!

### Next Steps

1. **With Real Datadog**:
   - Get API keys from Datadog
   - Update `.env` with your keys
   - Run: `python main.py --k6-result ../k6/sample_results.json`

2. **With Real k6 Tests**:
   - Install k6: `https://k6.io/docs/getting-started/installation/`
   - Run: `k6 run k6/tests/api_tests.js`
   - Parse results: `python main.py --k6-result k6/results.json`

3. **With AI Analysis**:
   - Install Docker
   - Run: `cd docker && docker-compose up -d`
   - Pull model: `docker exec api_test_analysis_ollama ollama pull gemma:2b`
   - Update `.env`: `OLLAMA_MODEL=gemma:2b`
   - Run analysis

### Full Documentation

- [Setup Instructions](docs/SETUP.md) - Detailed setup
- [Architecture](docs/ARCHITECTURE.md) - System design
- [Data Model](docs/DATA_MODEL.md) - Datadog schema
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Development phases

---

**Total Time**: ~5 minutes ⏱️
