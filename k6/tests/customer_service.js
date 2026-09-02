import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
const successCounter = new Counter('customer_successful_requests');
const failureCounter = new Counter('customer_failed_requests');
const requestDuration = new Trend('customer_request_duration');

// Base URL for testing
const BASE_URL = __ENV.BASE_URL || 'https://httpbin.org';

export const options = {
  stages: [
    { duration: '5s', target: 2 },   // Ramp up
    { duration: '10s', target: 2 },  // Stay at 2 VUs
    { duration: '5s', target: 0 },   // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'],
  },
};

// Generate execution ID
const executionId = `gh_run_${Date.now()}`;

// Result collector
const results = [];

export default function () {
  group('Customer Service - CreateCustomer', () => {
    const payload = JSON.stringify({
      name: `Customer_${randomString(8)}`,
      email: `customer_${randomString(8)}@example.com`,
      address: '123 Main St, Anytown',
      phone: '+1-555-0100',
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Service': 'customer',
        'X-Test-Name': 'CreateCustomer',
      },
    };

    const res = http.post(`${BASE_URL}/post`, payload, params);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 1000ms': (r) => r.timings.duration < 1000,
    });

    requestDuration.add(res.timings.duration);

    if (success) {
      successCounter.add(1);
    } else {
      failureCounter.add(1);
    }

    results.push({
      service: 'Customer',
      test_name: 'CreateCustomer',
      method: 'POST',
      endpoint: '/customers',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Customer Service - GetCustomer', () => {
    const params = {
      headers: {
        'X-Test-Service': 'customer',
        'X-Test-Name': 'GetCustomer',
      },
    };

    const res = http.get(`${BASE_URL}/get?id=123`, params);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 500ms': (r) => r.timings.duration < 500,
    });

    requestDuration.add(res.timings.duration);

    if (success) {
      successCounter.add(1);
    } else {
      failureCounter.add(1);
    }

    results.push({
      service: 'Customer',
      test_name: 'GetCustomer',
      method: 'GET',
      endpoint: '/customers/{id}',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Customer Service - UpdateCustomer', () => {
    const payload = JSON.stringify({
      name: `UpdatedCustomer_${randomString(8)}`,
      address: '456 Oak St, Sometown',
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Service': 'customer',
        'X-Test-Name': 'UpdateCustomer',
      },
    };

    const res = http.put(`${BASE_URL}/put`, payload, params);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 800ms': (r) => r.timings.duration < 800,
    });

    requestDuration.add(res.timings.duration);

    if (success) {
      successCounter.add(1);
    } else {
      failureCounter.add(1);
    }

    results.push({
      service: 'Customer',
      test_name: 'UpdateCustomer',
      method: 'PUT',
      endpoint: '/customers/{id}',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Customer Service - DeleteCustomer', () => {
    const params = {
      headers: {
        'X-Test-Service': 'customer',
        'X-Test-Name': 'DeleteCustomer',
      },
    };

    const res = http.delete(`${BASE_URL}/delete?id=123`, params);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 500ms': (r) => r.timings.duration < 500,
    });

    requestDuration.add(res.timings.duration);

    if (success) {
      successCounter.add(1);
    } else {
      failureCounter.add(1);
    }

    results.push({
      service: 'Customer',
      test_name: 'DeleteCustomer',
      method: 'DELETE',
      endpoint: '/customers/{id}',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });
}

// Export summary at end of test
export function teardown() {
  // Output results to stdout
  console.log(JSON.stringify({
    k6_meta: {
      execution_id: executionId,
      scenario: 'customer_service',
      duration: `${__DURATION}s`,
      vus: __VUS,
      timestamp: new Date().toISOString(),
    },
    results: results,
  }, null, 2));
}
