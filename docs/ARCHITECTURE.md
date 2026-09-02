# Architecture Document

Comprehensive technical architecture of the Intelligent API Test-Result Analysis POC.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Module Design](#module-design)
5. [Key Design Decisions](#key-design-decisions)
6. [Extension Points](#extension-points)

## System Overview

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXECUTION LAYER                             │
│  ┌──────────────────┐                                            │
│  │ GitHub Actions   │──► k6 Tests ──► Test Results JSON         │
│  └──────────────────┘                                            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               INGESTION & NORMALIZATION LAYER                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Result Parser → Normalize → Datadog Send → Index            ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATADOG (Source of Truth)                     │
│  • Events (execution results)                                    │
│  • Metrics (pass/fail counts, patterns)                          │
│  • Logs (error messages, k6 logs)                                │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│             PYTHON ANALYSIS ORCHESTRATION ENGINE                 │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ Datadog      │  │ Historical      │  │ Failure Pattern  │   │
│  │ Query        │──│ Comparison &    │──│ Classification   │   │
│  │ (prev 10)    │  │ Analysis        │  │ (Deterministic)  │   │
│  └──────────────┘  └─────────────────┘  └──────────────────┘   │
│         │                                                        │
│  ┌──────▼──────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │ Jira Correlation│  │ Ollama/LLM    │  │ Result           │   │
│  │ (Mock JSON)     │──│ Failure       │──│ Aggregation      │   │
│  │ + Matching      │  │ Detection     │  │ & Publishing     │   │
│  └─────────────────┘  └───────────────┘  └──────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│            DATADOG DASHBOARD & VISUALIZATION                     │
│  • Service/Test table with analysis results                      │
│  • Historical patterns (10-day comparison)                       │
│  • AI failure reasons                                            │
│  • Jira correlation                                              │
│  • Filters & drill-down capabilities                             │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Ingestion Module (`modules/ingestion/`)

**Purpose**: Parse and normalize k6 test results for Datadog ingestion.

**Components**:
- `k6_result_parser.py`: Parses k6 JSON output, validates structure
- `datadog_ingestion.py`: Sends normalized results to Datadog

**Key Interfaces**:
```python
class K6ResultParser:
    def parse_k6_json(path: str) -> K6ExecutionResult
    def normalize_results(execution) -> List[Dict]

class DatadogIngestion:
    def ingest_test_results(results: List, execution_id: str) -> bool
```

**Responsibility**:
- ✓ Parse k6 output format
- ✓ Extract test metadata
- ✓ Normalize to standard format
- ✓ Send events to Datadog
- ✓ Send metrics to Datadog

**Design Rationale**:
- Separate parsing from ingestion for testability
- Pydantic models for validation
- Normalized format decouples k6 from Datadog schema

### 2. Datadog Client (`modules/datadog/`)

**Purpose**: Abstraction layer for Datadog API interactions.

**Components**:
- `datadog_client.py`: HTTP wrapper for Datadog APIs

**Key Interfaces**:
```python
class DatadogClient:
    def send_event(event: Dict) -> bool
    def send_metrics(metrics: List) -> bool
    def query_events(query: str) -> List[Dict]
    def get_previous_executions(service, test) -> List[Dict]
```

**Responsibility**:
- ✓ Handle Datadog API authentication
- ✓ Retry logic and error handling
- ✓ Query historical data
- ✓ Send analysis results

**Design Rationale**:
- Centralized API wrapper prevents scattered HTTP calls
- Encapsulates authentication and error handling
- Easy to mock for testing
- Can be replaced with real Jira API later

### 3. Analysis Module (`modules/analysis/`)

**Purpose**: Perform deterministic analysis on test results.

**Components**:
- `historical_analyzer.py`: Retrieves and analyzes historical data
- `failure_classifier.py`: Classifies failure patterns
- `classification_rules.py`: Configurable classification logic

**Key Interfaces**:
```python
class HistoricalAnalyzer:
    def get_historical_data(service, test) -> List
    def calculate_statistics(current, historical) -> Dict

class FailureClassifier:
    def classify_test_result(service, test, status, historical) -> Dict

def classify_failure_pattern(current_status, historical_statuses):
    -> ClassificationResult
```

**Responsibility**:
- ✓ Query Datadog for previous 10 executions
- ✓ Calculate pass/fail statistics
- ✓ Classify failure patterns (Healthy/New/Persistent/Flaky/Resolved)
- ✓ All logic is deterministic (NO AI)

**Design Rationale**:
- Pure functions for testability
- Configurable thresholds in classification_rules.py
- No external dependencies (except Datadog client)
- Business rules are explicit, not hidden in code

**Classification Logic** (see classification_rules.py for details):
```
Persistent: failure_rate >= 70%
Flaky: 2+ alternations between PASS/FAIL
Resolved: previous failures + current PASS
New Failure: mostly passing historical + current FAIL
Healthy: current PASS + low historical failures
```

### 4. Jira Module (`modules/jira/`)

**Purpose**: Correlate failures with Jira issues.

**Components**:
- `jira_correlation.py`: Matches failures to Jira dataset
- `mock_jira.json`: Sample Jira dataset (replaceable with real API)

**Key Interfaces**:
```python
class JiraCorrelation:
    def find_matching_issue(service, test, failure_category) -> Dict
    def correlate_failure(service, test, pattern, category) -> Dict
```

**Return Format**:
```python
{
    'jira_found': True/False,
    'jira_id': 'PROJ-101' or None,
    'jira_status': 'In Progress' or None,
    'recommendation': 'Human-readable recommendation'
}
```

**Responsibility**:
- ✓ Search mock Jira dataset for matching issues
- ✓ Match by service + test + failure category
- ✓ Return recommendation
- ✓ Does NOT create issues (user decides)

**Design Rationale**:
- Abstract interface (swappable with real Jira API)
- Simple JSON-based dataset for POC
- No automatic issue creation (safety/control)
- Configurable matching logic

### 5. AI Module (`modules/ai/`)

**Purpose**: AI-powered failure analysis using local Ollama LLM.

**Components**:
- `ollama_client.py`: HTTP wrapper for Ollama API
- `failure_analyzer.py`: Analyzes failures using LLM

**Key Interfaces**:
```python
class OllamaClient:
    def health_check() -> bool
    def generate_response(prompt: str) -> str

class FailureAnalyzer:
    def analyze_failure(service, test, http_status, error, logs) -> Dict
```

**Return Format**:
```python
{
    'failure_reason': 'Brief explanation',
    'failure_category': 'One of: Authentication, Authorization, ...Unknown',
    'evidence': 'Supporting evidence from logs',
    'confidence': 'High/Medium/Low'
}
```

**Responsibility**:
- ✓ Only analyzes FAILED tests
- ✓ Constructs structured prompts
- ✓ Parses LLM JSON responses
- ✓ Validates output against known categories
- ✓ Returns "Unknown/Insufficient evidence" when needed
- ✓ Provides sensible defaults if Ollama unavailable

**Design Rationale**:
- AI is ONLY for failure reason detection
- All other analysis is deterministic
- Local LLM (no API costs, privacy)
- Graceful degradation if Ollama unavailable
- Structured prompts for consistent output
- Validation ensures output quality

### 6. Reporting Module (`modules/reporting/`)

**Purpose**: Aggregate results and publish analysis.

**Components**:
- `result_aggregator.py`: Combines all analysis components
- `summary_generator.py`: Creates human-readable summaries
- `datadog_publisher.py`: Sends analysis back to Datadog

**Key Interfaces**:
```python
class ResultAggregator:
    def aggregate_analysis(current, historical, classifications, jira, ai) -> List

class SummaryGenerator:
    def generate_summary(aggregated) -> str
    def generate_detailed_summary(aggregated) -> str

class DatadogPublisher:
    def publish_analysis(results, dry_run) -> bool
```

**Responsibility**:
- ✓ Combine all analysis components
- ✓ Filter and organize results
- ✓ Generate human-readable summaries
- ✓ Publish analysis results to Datadog
- ✓ Create dashboard metrics

**Design Rationale**:
- Final aggregation consolidates all analysis
- Summaries are deterministic (no AI)
- Dry-run mode for testing without Datadog impact
- Metrics sent back for dashboard visualization

## Data Flow

### Complete Request/Response Flow

```
1. GitHub Actions runs k6 tests
   ↓
   k6 outputs JSON with test results
   ↓

2. Python Analysis Engine receives results
   ↓
   K6ResultParser.parse_k6_json()
   ↓
   Normalized results: List[Dict]
   ↓

3. Ingest into Datadog
   ↓
   DatadogIngestion.ingest_test_results()
   ↓
   Send events + metrics to Datadog
   ↓

4. Query historical data
   ↓
   HistoricalAnalyzer.get_historical_data()
   ↓
   DatadogClient.get_previous_executions() [queries Datadog]
   ↓
   Returns previous 10 executions
   ↓

5. Analyze each Service/Test
   ↓
   FOR each test result:
       ├─ HistoricalAnalyzer.calculate_statistics()
       │  └─ Calculate pass/fail rates
       │
       ├─ FailureClassifier.classify_test_result()
       │  └─ Determine failure pattern (deterministic)
       │
       ├─ JiraCorrelation.correlate_failure()
       │  └─ Match to Jira dataset
       │
       └─ IF status = FAIL:
          └─ FailureAnalyzer.analyze_failure() [uses Ollama]
             └─ Detect likely failure reason (AI)
   ↓

6. Aggregate results
   ↓
   ResultAggregator.aggregate_analysis()
   ↓
   Combines: current + historical + classification + jira + ai
   ↓

7. Generate summary
   ↓
   SummaryGenerator.generate_summary()
   ↓
   "100 tests: 91 passed, 9 failed. 5 persistent, 2 flaky, ..."
   ↓

8. Publish to Datadog
   ↓
   DatadogPublisher.publish_analysis()
   ↓
   Send analysis events + metrics to Datadog
   ↓

9. Dashboard visualization
   ↓
   Datadog dashboard displays all results
```

### Data Model in Datadog

```
Events (per execution):
├─ Service/Test name
├─ Current status (PASS/FAIL)
├─ HTTP status
├─ Duration
└─ Error message

Metrics (per execution):
├─ test.execution_count (increment)
├─ test.pass_count (increment if PASS)
├─ test.fail_count (increment if FAIL)
├─ test.duration_ms (gauge)
├─ test.analysis.failure_pattern (categorical)
├─ test.analysis.jira_found (boolean)
└─ test.analysis.ai_confidence (gauge)

Logs:
├─ K6 execution logs
├─ Error messages
├─ Response bodies
└─ AI analysis reasoning

Tags (all):
├─ environment:poc
├─ service:customer
├─ test:create_customer
├─ status:pass/fail
└─ execution_id:gh_run_12345
```

## Module Design

### Entry Point: `main.py`

```python
class AnalysisEngine:
    def run_analysis(k6_result_file):
        1. Parse k6 results
        2. Ingest into Datadog
        3. Query historical data
        4. Classify failures
        5. Correlate Jira
        6. AI analysis (if FAIL)
        7. Aggregate results
        8. Generate summary
        9. Publish to Datadog
```

### Dependency Injection Pattern

```
AnalysisEngine
├── DatadogClient
│   └── Used by: Ingestion, HistoricalAnalyzer, Publisher
├── HistoricalAnalyzer
│   └── Uses: DatadogClient
├── FailureClassifier
│   └── Uses: classification_rules (pure functions)
├── JiraCorrelation
│   └── Uses: mock_jira.json (configurable)
├── OllamaClient
│   └── Used by: FailureAnalyzer
├── FailureAnalyzer
│   └── Uses: OllamaClient
├── ResultAggregator
│   └── Pure transformation
├── SummaryGenerator
│   └── Pure transformation
└── DatadogPublisher
    └── Uses: DatadogClient
```

### Error Handling Strategy

- **Graceful Degradation**: If Ollama unavailable, use heuristic-based analysis
- **Logging**: All errors logged with context
- **Dry-Run Mode**: Safe testing without Datadog impact
- **No Crashes**: Failures in one component don't stop pipeline

## Key Design Decisions

### 1. Datadog as Source of Truth

**Decision**: Store all historical data in Datadog, not local database.

**Rationale**:
- Simplifies architecture (no database management)
- Single source of truth
- Leverages Datadog's retention policies
- Queries via Datadog API instead of local DB

**Trade-off**: Dependent on Datadog availability

### 2. Deterministic Analysis + AI Separation

**Decision**: Keep analysis deterministic; use AI only for failure reason detection.

**Rationale**:
- Deterministic rules are auditable and reproducible
- Classification thresholds can be tuned
- AI is unreliable for counting/logic, good for summarization
- Reduces AI complexity and cost

**Trade-off**: Limited to predefined failure categories

### 3. Mock Jira Dataset

**Decision**: Use JSON file for POC; designed for real API replacement.

**Rationale**:
- No corporate Jira access needed for POC
- Easy to extend to real Jira API
- Demonstrates correlation logic
- Simple test data

**Trade-off**: Not synchronized with real Jira (manual updates)

### 4. Local Ollama Instead of API

**Decision**: Run Ollama locally; no cloud APIs.

**Rationale**:
- No API costs
- Data privacy (no sending logs to cloud)
- Offline capability
- Full control

**Trade-off**: Requires local compute; smaller models than cloud

### 5. Modular Architecture

**Decision**: Separate modules for each concern.

**Rationale**:
- Easy to test independently
- Easy to replace components (e.g., Jira)
- Clear responsibilities
- Reusable components

**Trade-off**: More files/complexity than monolithic

### 6. Configuration via Environment Variables

**Decision**: All config in .env (12-factor app).

**Rationale**:
- No hardcoded secrets
- Easy deployment variations
- .env.example documents all options
- Standard Python practice

**Trade-off**: Must manage .env files carefully

## Extension Points

### To Replace GitHub Actions with Testway

1. Modify `.github/workflows/run-tests.yml` to trigger from Testway webhook
2. Adjust `modules/ingestion/k6_result_parser.py` to parse Testway output format
3. Update tags in `modules/ingestion/datadog_ingestion.py`
4. Core analysis logic remains unchanged ✓

### To Add Real Jira Integration

1. Create `modules/jira/jira_api_client.py` with real Jira API calls
2. Update `JiraCorrelation.find_matching_issue()` to call real API
3. Test with `test_jira_correlation.py`
4. Swap out mock dataset ✓

### To Replace Ollama with Cloud LLM

1. Create `modules/ai/cloud_llm_client.py` (e.g., OpenAI, Anthropic)
2. Update `FailureAnalyzer.__init__()` to use cloud client
3. Adjust cost considerations
4. Keep same interface ✓

### To Add Database for Audit Trail

1. Create `modules/persistence/database.py`
2. Store analysis results in DB after Datadog publish
3. Create backup/recovery utilities
4. Optional audit logging ✓

### To Add Notifications

1. Create `modules/notifications/slack.py` or `modules/notifications/email.py`
2. Notify on critical failures
3. Send summary reports
4. Configurable thresholds ✓

---

**Next**: See [DATA_MODEL.md](DATA_MODEL.md) for Datadog schema details.
