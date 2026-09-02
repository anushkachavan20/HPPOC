import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
const successCounter = new Counter('successful_requests');
const failureCounter = new Counter('failed_requests');
const requestDuration = new Trend('request_duration');

// Base URL for testing (using httpbin.org as mock API)
const BASE_URL = __ENV.BASE_URL || 'https://httpbin.org';

export const options = {
  stages: [
    { duration: '5s', target: 2 },  // Ramp up
    { duration: '10s', target: 2 }, // Stay at 2 VUs
    { duration: '5s', target: 0 },  // Ramp down
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

  group('Order Service - CreateOrder', () => {
    const payload = JSON.stringify({
      customer_id: '123',
      items: [
        { product_id: 'PROD_001', quantity: 2, price: 29.99 },
      ],
      total: 59.98,
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

  group('Payment Service - CreatePayment', () => {
    const payload = JSON.stringify({
      order_id: '456',
      amount: 59.98,
      currency: 'USD',
      method: 'credit_card',
      card_last4: '4242',
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Service': 'payment',
        'X-Test-Name': 'CreatePayment',
      },
    };

    const res = http.post(`${BASE_URL}/post`, payload, params);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 2000ms': (r) => r.timings.duration < 2000,
    });

    requestDuration.add(res.timings.duration);

    if (success) {
      successCounter.add(1);
    } else {
      failureCounter.add(1);
    }

    results.push({
      service: 'Payment',
      test_name: 'CreatePayment',
      method: 'POST',
      endpoint: '/payments',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Payment Service - GetPayment', () => {
    const params = {
      headers: {
        'X-Test-Service': 'payment',
        'X-Test-Name': 'GetPayment',
      },
    };

    const res = http.get(`${BASE_URL}/get?payment_id=789`, params);
    const success = check(res, {
      'status is 200': (r) => r.status === 200,
    });

    requestDuration.add(res.timings.duration);

    if (success) {
      successCounter.add(1);
    } else {
      failureCounter.add(1);
    }

    results.push({
      service: 'Payment',
      test_name: 'GetPayment',
      method: 'GET',
      endpoint: '/payments/{id}',
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
  // Output results to stdout (will be captured by GitHub Actions)
  console.log(JSON.stringify({
    k6_meta: {
      execution_id: executionId,
      scenario: 'api_tests',
      duration: `${__DURATION}s`,
      vus: __VUS,
      timestamp: new Date().toISOString(),
    },
    results: results,
  }, null, 2));
}
