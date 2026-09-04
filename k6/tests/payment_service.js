import http from "k6/http";
import { check, group } from "k6";

/*
 * Service 3: httpbin
 *
 * Purpose:
 * - Use a real public HTTP testing service
 * - GET requests only
 * - No fake business data
 * - No request bodies
 * - No create/update/delete operations
 * - Include a controlled HTTP 500 failure
 *
 * The Python parser determines PASS/FAIL from HTTP status:
 *
 * 2xx / 3xx -> PASS
 * 4xx / 5xx -> FAIL
 */

export const options = {
    vus: 1,
    iterations: 1,
};

const BASE_URL = "https://httpbin.org";
const failureScenario = __ENV.FAIL_SCENARIO || "none";

export default function () {

    // =========================================================
    // API 1 - Basic GET
    //
    // Expected: 200
    // =========================================================

    group("Payment Service - Get Payment", function () {

        const response = http.get(
            `${BASE_URL}/get`,
            {
                tags: {
                    service: "payment",
                    test: "Get Payment",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "Get Payment - HTTP 200": (r) =>
                r.status === 200,
        });
    });

    // =========================================================
    // API 2 - UUID endpoint
    //
    // Expected: 200
    //
    // The server generates the UUID.
    // We are not sending any fake data.
    // =========================================================

    group("Payment Service - Get Payment ID", function () {

        const response = http.get(
            `${BASE_URL}/uuid`,
            {
                tags: {
                    service: "payment",
                    test: "Get Payment ID",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "Get Payment ID - HTTP 200": (r) =>
                r.status === 200,
        });
    });

    // =========================================================
    // API 3 - Intentional HTTP 500
    //
    // httpbin provides an endpoint specifically for returning
    // a requested HTTP status.
    //
    // No business data is created, modified, or deleted.
    // =========================================================

    group("Payment Service - Server Error", function () {

        const failureStatus = ["401", "404", "500"].includes(failureScenario)
            ? Number(failureScenario)
            : 200;
        const response = http.get(
            `${BASE_URL}/status/${failureStatus}`,
            {
                tags: {
                    service: "payment",
                    test: "Server Error",
                    expected_status: String(failureStatus),
                    failure_type: failureStatus === 200 ? "none" : `http_${failureStatus}`,
                },
            }
        );

        check(response, {
                "Server Error - expected status": (r) =>
                r.status === failureStatus,
        });

        console.log(
            `Payment Server Error response: HTTP ${response.status}`
        );
    });
}