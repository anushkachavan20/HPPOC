# Intelligent API Test-Result Analysis POC
## Use Case and Solution Approach

**Document purpose:** Explain the business use case, the approach used in the POC, and how it replicates the existing Testway-to-Power BI reporting behavior.  
**Project:** Intelligent API Test-Result Analysis POC  
**Prepared on:** 13 September 2026

---

## 1. Background and Use Case

In the existing process, API test jobs were executed every day through Testway. After each execution, the test results were collected, processed, and pushed to a Power BI dashboard. The dashboard was used to review the daily health of APIs, identify failures, and track recurring issues over time.

This reporting flow became difficult to use because of an access issue with Power BI. The required test results and analysis were still being generated, but the team could not reliably access the dashboard to review them.

The purpose of this POC is to replicate the important behavior of that reporting process in a more accessible and controllable form:

```text
Daily API test job
        |
        v
Test result collection
        |
        v
Result parsing and analysis
        |
        v
Historical comparison and failure classification
        |
        v
Central reporting/observability output
```

The POC is not intended to replace Testway or reproduce the Power BI product itself. It reproduces the reporting and analysis logic that the team needs from the original workflow.

---

## 2. Original Testway Reporting Flow

The original business workflow can be described as follows:

1. Testway jobs ran API tests every day.
2. Each job produced test results for the relevant services and APIs.
3. The results were collected into a reporting dataset.
4. The dataset was used to create daily summaries and historical views.
5. The results were pushed to a Power BI dashboard.
6. Users reviewed the dashboard to identify failures, trends, and recurring problems.

The main value of the process was not only knowing whether a test passed or failed. It also provided a single place to understand:

- Which service and API test failed.
- Whether the failure was new or had happened repeatedly.
- Whether the behavior was intermittent or stable.
- Whether an existing Jira issue was related to the failure.
- Which failures needed investigation or follow-up.

---

## 3. Problem Statement

The Power BI access issue created a gap in the reporting workflow. The test jobs could still run, but the results were not easily available to the people who needed to analyze them.

This created several practical problems:

- Daily test results were harder to review.
- Historical comparison was less convenient.
- Recurring failures could not be identified quickly.
- Teams had to depend on manual investigation or alternate result files.
- The reporting process was coupled to access to one dashboard platform.

The POC addresses this gap by separating test execution, result analysis, and result visualization. The analysis engine can process the same type of test output and publish the information to an accessible reporting or observability destination.

---

## 4. POC Objective

The objective is to prove that the daily Testway reporting behavior can be reproduced using an independent analysis pipeline.

The POC demonstrates that we can:

1. Execute or consume API test results.
2. Normalize the results into a consistent format.
3. Calculate pass/fail summaries.
4. Compare current results with previous executions.
5. Classify the behavior of failures.
6. Correlate failures with Jira issues.
7. Produce a human-readable report and structured output.
8. Publish the analyzed information to Datadog when configured.

The expected outcome is an accessible and repeatable alternative for reviewing API test health when Power BI access is unavailable.

---

## 5. Approach Used

The POC uses a modular pipeline. Each stage has one responsibility and can be replaced independently.

### Stage 1: Test execution

k6 scripts represent the API tests that were previously executed by the daily Testway jobs. The tests are organized by service:

- Customer service
- Order service
- Payment service

The customer service example uses read-only HTTP requests against public endpoints. Controlled HTTP responses such as `401`, `404`, and `500` can be used to demonstrate failure handling without changing application data.

In a production implementation, the k6 execution step can be replaced by Testway output. The analysis logic does not need to depend on the system that ran the tests, provided that the result format is mapped to the expected normalized structure.

### Stage 2: Result ingestion and normalization

The Python ingestion layer reads k6 JSON or JSONL output and converts it into a consistent internal representation.

Each normalized result contains information such as:

- Execution ID and timestamp
- Service name
- Test name
- HTTP status
- Expected status
- Pass/fail status
- Response duration
- Error message or response evidence

This normalization step is important because it separates the test execution tool from the analysis and reporting logic.

### Stage 3: Historical analysis

For each service and test, the current result is compared with previous executions. The target historical window is the previous ten executions when that data is available.

This provides context that a single daily result cannot provide. For example, a failed test may be:

- A new failure after a period of successful runs.
- A persistent failure that fails in most executions.
- A flaky test that alternates between pass and fail.
- A resolved failure that is passing again.
- A healthy test with an isolated or low failure rate.

### Stage 4: Deterministic failure classification

The classification rules are implemented as explicit Python logic. This makes the result explainable and consistent.

| Classification | Meaning |
|---|---|
| Healthy | The current result passes and recent failures are low. |
| New Failure | The test was previously passing and is now failing. |
| Persistent Failure | The failure rate in the historical window meets the configured threshold. |
| Flaky Failure | The recent execution history shows repeated pass/fail alternation. |
| Resolved Failure | The test was failing previously and is currently passing. |

The classifier does not replace the raw test result. It adds context to help prioritize investigation.

### Stage 5: Jira correlation

The POC checks whether a failure matches an existing Jira issue. The current repository supports mock Jira data and includes a client structure for Jira Cloud integration.

The correlation output can include:

- Jira issue key
- Jira issue status
- Matching service, test, or failure category
- Recommendation when no matching issue is found

The POC does not automatically create Jira issues. This keeps the workflow under human control and avoids creating duplicate or incorrect defects.

### Stage 6: Reporting and publication

The analyzed results are aggregated into a summary and structured report. The repository supports local report output and Datadog publication.

Datadog acts as the accessible reporting and observability destination in this POC. It stores or exposes:

- Test execution events
- Pass/fail metrics
- Duration metrics
- Error logs
- Historical analysis results
- Failure-pattern and Jira-correlation information

This is the equivalent reporting purpose that Power BI served in the original workflow. The implementation is not a visual copy of Power BI; it provides the same operational information through a different reporting path.

---

## 6. Architecture Mapping

| Original workflow | POC implementation |
|---|---|
| Testway daily job | k6 scripts or an external Testway result supplied to the parser |
| Testway result export | k6 JSON/JSONL result file |
| Result preparation | `python/modules/ingestion/k6_result_parser.py` |
| Historical dashboard data | Datadog events, metrics, and logs |
| Daily pass/fail view | Python summary and Datadog metrics |
| Trend and recurring-failure analysis | `python/modules/analysis/` |
| Defect lookup | `python/modules/jira/` and mock Jira data |
| Power BI reporting purpose | Datadog dashboard/reporting output and generated reports |
| Manual investigation follow-up | Jira recommendation and human review |

The key design decision is to keep the analysis independent of the visualization tool. This means the same analyzed result can later be sent to Datadog, Power BI, another dashboard, or a report file without rewriting the classification logic.

---

## 7. End-to-End Flow in This Repository

The current POC flow is:

```text
k6 test script or sample result
        |
        v
K6ResultParser
        |
        v
Datadog ingestion layer
        |
        v
HistoricalAnalyzer
        |
        v
FailureClassifier
        |
        v
JiraCorrelation
        |
        v
ResultAggregator and SummaryGenerator
        |
        v
Local report files and optional Datadog publication
```

The main orchestration is implemented in `python/main.py`. It coordinates parsing, ingestion, history lookup, classification, Jira correlation, aggregation, and reporting.

For a repeatable demonstration without external credentials:

```powershell
Set-Location C:\Users\P7120242\Desktop\POC\python
python main.py --k6-result ..\k6\sample_results.json --dry-run
```

The dry-run option is useful for validating the reporting behavior without sending data to Datadog.

---

## 8. Why This Approach Was Selected

### Separation of execution and analysis

The test runner should not own the business logic for trend analysis. Whether results come from Testway, k6, or another test platform, they can be normalized and analyzed consistently.

### Datadog as an accessible source of truth

The POC uses Datadog to store operational test information and make it searchable through tags, metrics, events, and logs. This provides an alternative location for the information previously consumed through Power BI.

### Deterministic classification

Failure categories are calculated using explicit rules rather than being generated by an AI model. This makes the classification predictable, auditable, and easier to explain to stakeholders.

### Controlled Jira integration

The system correlates failures with Jira but does not automatically create issues. A person can review the evidence before deciding whether new work is required.

### Modular implementation

The parser, Datadog client, historical analyzer, classifier, Jira correlation, and reporting components are separated. This allows the POC to evolve without replacing the complete workflow.

---

## 9. Current Scope and Limitations

- The repository demonstrates the reporting and analysis behavior; it does not reproduce the Power BI user interface.
- The current local execution uses k6 scripts and sample result files. A production Testway integration would require mapping the Testway export format to the parser input.
- Historical classifications are meaningful only when previous executions are available.
- Datadog publication requires valid Datadog configuration and credentials.
- Jira correlation can use mock data for the POC and real Jira Cloud configuration for integration testing.
- The current `main.py` documents Ollama/LLM analysis as disabled for this POC phase. AI modules are present as an extension point, but AI behavior should not be presented as part of the active end-to-end flow unless it has been enabled and verified.
- The POC recommends Jira follow-up but does not create issues automatically.

---

## 10. Expected Business Outcome

This POC provides a working alternative path for reviewing daily API test results when Power BI access is unavailable.

The expected business benefits are:

- Continued visibility into daily API test health.
- Faster identification of new and recurring failures.
- Consistent analysis across services and test tools.
- Better context for engineering triage.
- Traceability from a failure to historical executions and Jira work.
- Reduced dependency on a single dashboard platform.
- A foundation that can later integrate directly with Testway and publish to the organization’s preferred reporting tool.

---

## 11. Suggested Demonstration Narrative

The POC can be explained in the following sequence:

> In the original process, Testway ran API jobs every day and the results were pushed to a Power BI dashboard. Due to a Power BI access issue, the team needed another way to access the same operational information. This POC replicates the reporting behavior by consuming API test results, normalizing them, comparing them with historical executions, classifying failures, correlating them with Jira, and publishing the resulting analysis to an accessible reporting destination. The goal is to preserve the decision-support value of the original dashboard, not to recreate the Power BI interface.

The main demonstration should show the input result, the analysis stages, the failure classification, the Jira correlation result, and the final generated or published report.

---

## 12. Conclusion

The POC validates an approach for decoupling daily API test analysis from Power BI access. Testway or k6 can provide the execution result, Python can perform the analysis, Jira can provide issue context, and Datadog or another reporting destination can expose the final information.

This gives the team a practical fallback for the current Power BI access problem and establishes a reusable architecture for future integration with Testway and enterprise reporting platforms.

---

## 13. Datadog Historical Data

Datadog stores the test history in more than one data type:

- **Events:** Each test execution is published with tags such as `service`, `test`, `testcase_id`, `status`, and `execution_id`. These events retain the detailed result and are used by the historical analyzer.
- **Metrics:** Counts and measurements such as pass/fail totals, response time, service totals, API totals, Jira actions, and failure occurrences are published as time-series metrics.
- **Logs:** Detailed execution or failure messages can be stored as logs when log ingestion is enabled.

For historical classification, the Python `HistoricalAnalyzer` asks Datadog for previous events matching the same service and API test. The Datadog client retrieves the most recent executions, removes the current execution, ignores duplicate analysis events, and deduplicates records by `execution_id`. The analyzer then calculates the previous pass count, fail count, pass rate, failure rate, status sequence, and trend.

The default comparison window is the previous ten executions. Datadog retention is controlled by the Datadog account and product plan, so the POC can only analyze history that is still retained and accessible through the configured account. The POC does not use a separate local historical database.

Testcase IDs are now included in the normalized result, Datadog tags, analysis event text, and Jira correlation. Jira searches first for a `testcase:<ID>` label. Existing issues created before testcase IDs were introduced remain compatible through the legacy `service`, `api`, and `failure-type` labels.
