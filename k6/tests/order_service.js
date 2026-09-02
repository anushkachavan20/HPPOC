import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
const successCounter = new Counter('order_successful_requests');
const failureCounter = new Counter('order_failed_requests');
const requestDuration = new Trend('order_request_duration');

// Base URL for testing
const BASE_URL = __ENV.BASE_URL || 'https://httpbin.org';

export const options = {
  stages: [
    { duration: '5s', target: 2 },   // Ramp up
    { duration: '10s', target: 2 },  // Stay at 2 VUs
    { duration: '5s', target: 0 },   // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1000'],
  },
};

// Generate execution ID
const executionId = `gh_run_${Date.now()}`;

// Result collector
const results = [];

export default function () {
  group('Order Service - CreateOrder', () => {
    const payload = JSON.stringify({
      customer_id: `CUST_${randomString(6)}`,
      items: [
        { product_id: 'PROD_001', quantity: 2, price: 29.99 },
        { product_id: 'PROD_002', quantity: 1, price: 49.99 },
      ],
      total: 109.97,
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Service': 'order',
        'X-Test-Name': 'CreateOrder',
      },
    };

    const res = http.post(`${BASE_URL}/post`, payload, params);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 1500ms': (r) => r.timings.duration < 1500,
    });

    requestDuration.add(res.timings.duration);

    if (success) {
      successCounter.add(1);
    } else {
      failureCounter.add(1);
    }

    results.push({
      service: 'Order',
      test_name: 'CreateOrder',
      method: 'POST',
      endpoint: '/orders',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Order Service - GetOrder', () => {
    const params = {
      headers: {
        'X-Test-Service': 'order',
        'X-Test-Name': 'GetOrder',
      },
    };

    const res = http.get(`${BASE_URL}/get?order_id=456`, params);
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
      service: 'Order',
      test_name: 'GetOrder',
      method: 'GET',
      endpoint: '/orders/{id}',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Order Service - UpdateOrder', () => {
    const payload = JSON.stringify({
      status: 'shipped',
      tracking_number: `TRACK_${randomString(8)}`,
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Service': 'order',
        'X-Test-Name': 'UpdateOrder',
      },
    };

    const res = http.put(`${BASE_URL}/put`, payload, params);
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
      service: 'Order',
      test_name: 'UpdateOrder',
      method: 'PUT',
      endpoint: '/orders/{id}',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Order Service - CancelOrder', () => {
    const params = {
      headers: {
        'X-Test-Service': 'order',
        'X-Test-Name': 'CancelOrder',
      },
    };

    const res = http.delete(`${BASE_URL}/delete?order_id=456`, params);
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
      service: 'Order',
      test_name: 'CancelOrder',
      method: 'DELETE',
      endpoint: '/orders/{id}',
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
      scenario: 'order_service',
      duration: `${__DURATION}s`,
      vus: __VUS,
      timestamp: new Date().toISOString(),
    },
    results: results,
  }, null, 2));
}
