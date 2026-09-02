# Datadog Data Model

Detailed specification of how test execution data is structured and stored in Datadog.

## Table of Contents

1. [Overview](#overview)
2. [Event Schema](#event-schema)
3. [Metrics Schema](#metrics-schema)
4. [Logs Schema](#logs-schema)
5. [Tags & Attributes](#tags--attributes)
6. [Query Examples](#query-examples)
7. [Dashboard Queries](#dashboard-queries)

## Overview

The POC uses three Datadog features to store test data:

1. **Events** - Individual test execution results
2. **Metrics** - Aggregated counts and patterns
3. **Logs** - Detailed error messages and k6 logs

All data is tagged consistently for easy querying and filtering.

## Event Schema

### Test Execution Event

Each k6 test result creates a Datadog Event.

**Example Event**:

```json
{
  "title": "API Test: Customer/CreateCustomer",
  "text": "Status: PASS\nHTTP Status: 201\nDuration: 125ms",
  "timestamp": 1725019800,
  "alert_type": "success",
  "tags": [
    "environment:poc",
    "service:customer",
    "test:create_customer",
    "status:pass",
    "http_status:201",
    "execution_id:gh_run_12345",
    "test_type:k6"
  ],
  "metadata": {
    "execution_id": "gh_run_12345",
    "service": "customer",
    "test": "create_customer",
    "status": "PASS",
    "http_status": 201,
    "duration_ms": 125,
    "error_message": ""
  }
}
```

### Failure Event

Failed tests have additional detail:

```json
{
  "title": "API Test: Order/CreateOrder",
  "text": "Status: FAIL\nHTTP Status: 500\nError: Database connection timeout",
  "timestamp": 1725019805,
  "alert_type": "error",
  "tags": [
    "environment:poc",
    "service:order",
    "test:create_order",
    "status:fail",
    "http_status:500",
    "execution_id:gh_run_12345"
  ],
  "metadata": {
    "execution_id": "gh_run_12345",
    "service": "order",
    "test": "create_order",
    "status": "FAIL",
    "http_status": 500,
    "duration_ms": 2500,
    "error_message": "Database connection timeout"
  }
}
```

### Analysis Result Event

After analysis, a second event is created with analysis results:

```json
{
  "title": "Analysis: Order/CreateOrder - Persistent Failure",
  "text": "Status: FAIL\nPattern: Persistent Failure\nJira: PROJ-102 (In Progress)\nAI Category: Database\nReason: Database connection pool exhausted",
  "tags": [
    "environment:poc",
    "service:order",
    "test:create_order",
    "analysis:true",
    "pattern:persistent_failure",
    "jira_id:PROJ-102"
  ]
}
```

## Metrics Schema

### Per-Test Metrics

Each test sends multiple metrics with tags.

**Pattern**: `metric_name` with tags for service/test/execution

### Execution Metrics

Sent immediately after ingestion:

```
test.execution_count
  value: 1
  tags:
    - environment:poc
    - service:customer
    - test:create_customer
    - execution_id:gh_run_12345

test.result
  value: 1 (for PASS) or 0 (for FAIL)
  tags:
    - environment:poc
    - service:customer
    - test:create_customer
    - execution_id:gh_run_12345

test.duration_ms
  value: 125
  tags:
    - environment:poc
    - service:customer
    - test:create_customer
    - execution_id:gh_run_12345
```

### Aggregated Metrics (Per Execution)

```
test.total_count
  value: 10 (total tests in run)
  tags:
    - environment:poc
    - execution_id:gh_run_12345

test.pass_count
  value: 7
  tags:
    - environment:poc
    - execution_id:gh_run_12345

test.fail_count
  value: 3
  tags:
    - environment:poc
    - execution_id:gh_run_12345
```

### Analysis Metrics (Per Test)

Sent after analysis:

```
test.analysis.failure_pattern
  value: 1
  tags:
    - environment:poc
    - service:order
    - test:create_order
    - pattern:persistent_failure

test.analysis.pattern_count
  value: 1 (count per pattern)
  tags:
    - environment:poc
    - pattern:persistent_failure

test.analysis.jira_found
  value: 1 (true) or 0 (false)
  tags:
    - environment:poc
    - service:order
    - test:create_order
    - jira_found:true
    - jira_id:PROJ-102

test.analysis.ai_confidence
  value: 0.95 (confidence score)
  tags:
    - environment:poc
    - service:order
    - test:create_order
    - ai_category:database
```

## Logs Schema

### K6 Execution Logs

Detailed k6 logs are sent as structured logs:

```json
{
  "timestamp": "2026-09-01T10:30:05Z",
  "message": "VU 1: Sending POST request to /orders",
  "service": "order",
  "test": "create_order",
  "execution_id": "gh_run_12345",
  "log_level": "INFO",
  "log_type": "k6_execution",
  "ddtags": "environment:poc,service:order,test:create_order"
}
```

### Error Logs

When a test fails:

```json
{
  "timestamp": "2026-09-01T10:30:05Z",
  "message": "Request failed: HTTP 500 Database connection timeout",
  "service": "order",
  "test": "create_order",
  "execution_id": "gh_run_12345",
  "log_level": "ERROR",
  "http_status": 500,
  "error_message": "Database connection timeout",
  "response_body": "{\"error\": \"Database connection pool exhausted\"}",
  "ddtags": "environment:poc,service:order,test:create_order,status:fail"
}
```

## Tags & Attributes

### Standard Tags (Applied to All)

**Environment Tags**:
```
environment:poc              # Environment
analyzer:poc                # Component
test_type:k6                # Test framework
```

### Service/Test Tags

**Per-Test Tags**:
```
service:{service_name}      # Service (lowercase)
test:{test_name}            # Test/API name (lowercase)
status:{pass|fail}          # Current status
http_status:{code}          # HTTP response code
execution_id:{id}           # Execution ID from k6 meta
```

### Analysis Tags

**After Analysis**:
```
analysis:true               # Marks analysis results
pattern:{pattern_name}      # Failure pattern classification
jira_found:{true|false}     # Whether Jira issue exists
jira_id:{id}                # Jira issue ID if found
ai_category:{category}      # AI-detected failure category
```

### Valid Tag Values

**Status**:
- `pass` or `fail`

**Patterns**:
- `healthy`
- `new_failure`
- `persistent_failure`
- `flaky_failure`
- `resolved_failure`

**AI Categories**:
- `authentication`
- `authorization`
- `validation`
- `timeout`
- `network`
- `server_error`
- `database`
- `dependency`
- `configuration`
- `unknown`

## Query Examples

### Query Recent Test Results

**Datadog Logs Query**:
```
service:customer test:create_customer status:fail
```

**Datadog Events Query**:
```
tags:"service:customer" AND tags:"test:create_customer" AND tags:"status:fail"
```

### Query by Failure Pattern

**Logs**:
```
analysis:true pattern:persistent_failure
```

**Metrics** (via Metric Summary):
```
test.analysis.failure_pattern{pattern:persistent_failure}
```

### Query by Service

```
tags:"service:order" status:fail
```

### Query Recent Failures for Jira Matching

```
status:fail jira_found:false (within last 7 days)
```

### Query by AI Category

```
ai_category:database OR ai_category:timeout
```

## Dashboard Queries

### Key Metrics for Dashboard

**Total Pass Rate**:
```
avg:test.result{environment:poc}
```

**Failed Tests**:
```
sum:test.fail_count{environment:poc}
```

**Persistent Failures**:
```
sum:test.analysis.pattern_count{pattern:persistent_failure}
```

**Flaky Failures**:
```
sum:test.analysis.pattern_count{pattern:flaky_failure}
```

**Jira Coverage**:
```
sum:test.analysis.jira_found{jira_found:true}
```

### Dashboard Table Queries

**Service/Test Status Table**:

Query all test results:
```
tags:"environment:poc" tags:"service:*" tags:"test:*"
```

Aggregate by service and test:
- Service: `tags:"service:*"`
- Test: `tags:"test:*"`
- Status: `tags:"status:*"`
- Pattern: `tags:"pattern:*"`
- Jira: `tags:"jira_id:*"`

**Example Table Columns**:
1. Service (tag: `service`)
2. Test (tag: `test`)
3. Current Status (tag: `status`, latest)
4. 10-Day Pattern (metric: `test.analysis.failure_pattern`, tag: `pattern`)
5. Failure Count (calculated: sum of failures in past 10)
6. Jira Issue (tag: `jira_id`, or "No issue")
7. AI Reason (custom attribute or log analysis)

### Dashboard Filters

**Environment Filter**:
- Tag: `environment` = `poc`

**Service Filter**:
- Tag: `service` = selected service

**Status Filter**:
- Tag: `status` = `pass` or `fail`

**Pattern Filter**:
- Tag: `pattern` = selected pattern

## Data Retention & Query Tips

### Event Retention
- Free tier: 15 days
- Adjust retention policy in Datadog settings

### Metric Retention
- Custom metrics: 15 months
- Resolution: 1 point per minute

### Log Retention
- Free tier: 3 days
- Adjust in Log Management settings

### Performance Tips

1. **Use tags for filtering** - More efficient than text search
2. **Aggregate by service/test** - Reduces dashboard load
3. **Use time ranges** - Specific dates are faster than "all"
4. **Create saved searches** - Reuse common queries

### Example Dashboard Definition

```json
{
  "title": "API Test Analysis",
  "layout_type": "grid",
  "widgets": [
    {
      "type": "query_value",
      "title": "Total Tests",
      "query": "sum:test.total_count{environment:poc}"
    },
    {
      "type": "query_value",
      "title": "Pass Rate",
      "query": "avg:test.result{environment:poc}"
    },
    {
      "type": "timeseries",
      "title": "Pass/Fail Trend",
      "query": "sum:test.pass_count{environment:poc} vs sum:test.fail_count{environment:poc}"
    },
    {
      "type": "toplist",
      "title": "Top Failed Services",
      "query": "top(sum:test.fail_count{environment:poc}, 5, sum, desc)"
    },
    {
      "type": "table",
      "title": "Test Results",
      "queries": [
        {"query": "tags:* (complex table query)"}
      ]
    }
  ]
}
```

---

**Next**: See [SETUP.md](SETUP.md) for environment configuration.
