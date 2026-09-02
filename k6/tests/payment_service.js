import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
const successCounter = new Counter('payment_successful_requests');
const failureCounter = new Counter('payment_failed_requests');
const requestDuration = new Trend('payment_request_duration');

// Base URL for testing
const BASE_URL = __ENV.BASE_URL || 'https://httpbin.org';

export const options = {
  stages: [
    { duration: '5s', target: 2 },   // Ramp up
    { duration: '10s', target: 2 },  // Stay at 2 VUs
    { duration: '5s', target: 0 },   // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000'],
  },
};

// Generate execution ID
const executionId = `gh_run_${Date.now()}`;

// Result collector
const results = [];

export default function () {
  group('Payment Service - CreatePayment', () => {
    const payload = JSON.stringify({
      order_id: `ORD_${randomString(6)}`,
      amount: (Math.random() * 500 + 50).toFixed(2),
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
      'response time < 1000ms': (r) => r.timings.duration < 1000,
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

  group('Payment Service - RefundPayment', () => {
    const payload = JSON.stringify({
      payment_id: `PAY_${randomString(6)}`,
      reason: 'Customer request',
      amount: (Math.random() * 100 + 10).toFixed(2),
    });

    const params = {
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Service': 'payment',
        'X-Test-Name': 'RefundPayment',
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
      test_name: 'RefundPayment',
      method: 'POST',
      endpoint: '/payments/{id}/refund',
      status: success ? 'PASS' : 'FAIL',
      http_status: res.status,
      duration_ms: res.timings.duration,
      error: success ? null : `Status ${res.status}`,
      response_body: res.body.substring(0, 200),
      timestamp: new Date().toISOString(),
    });

    sleep(1);
  });

  group('Payment Service - VerifyPayment', () => {
    const params = {
      headers: {
        'X-Test-Service': 'payment',
        'X-Test-Name': 'VerifyPayment',
      },
    };

    const res = http.get(`${BASE_URL}/get?verification_id=verify_123`, params);
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
      service: 'Payment',
      test_name: 'VerifyPayment',
      method: 'GET',
      endpoint: '/payments/verify',
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
      scenario: 'payment_service',
      duration: `${__DURATION}s`,
      vus: __VUS,
      timestamp: new Date().toISOString(),
    },
    results: results,
  }, null, 2));
}
