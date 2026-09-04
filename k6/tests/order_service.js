import http from "k6/http";
import { check, group } from "k6";

/*
 * Service 2: ReqRes
 *
 * Purpose:
 * - Use a real public API
 * - GET requests only
 * - No fake request body
 * - No create/update/delete operations
 * - Include an intentional 401 failure scenario
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

const BASE_URL = "https://reqres.in";
const failureScenario = __ENV.FAIL_SCENARIO || "none";

export default function () {

    // =========================================================
    // API 1 - Get users
    //
    // Expected: 200
    // =========================================================

    group("ReqRes Service - GetUsers", function () {

        const response = http.get(
            `${BASE_URL}/api/users?page=2`,
            {
                tags: {
                    service: "reqres",
                    test: "GetUsers",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "GetUsers - HTTP 200": (r) =>
                r.status === 200,
        });
    });

    // =========================================================
    // API 2 - Get single user
    //
    // Expected: 200
    // =========================================================

    group("ReqRes Service - GetUser", function () {

        const response = http.get(
            `${BASE_URL}/api/users/2`,
            {
                tags: {
                    service: "reqres",
                    test: "GetUser",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "GetUser - HTTP 200": (r) =>
                r.status === 200,
        });
    });

    // =========================================================
    // API 3 - Unauthorized request
    //
    // This is intentionally configured to produce an HTTP 401.
    //
    // No data is created or modified.
    // No credentials are sent.
    //
    // This gives the POC an authentication failure that can
    // later be analyzed by the classification/Ollama layer.
    // =========================================================

    group("ReqRes Service - Unauthorized", function () {

        const failureStatus = ["401", "404", "500"].includes(failureScenario)
            ? Number(failureScenario)
            : 200;
        const response = http.get(
            failureStatus === 200
                ? `${BASE_URL}/api/users/2`
                : `https://httpbin.org/status/${failureStatus}`,
            {
                tags: {
                    service: "reqres",
                    test: "Unauthorized",
                    expected_status: String(failureStatus),
                    failure_type: failureStatus === 200 ? "none" : `http_${failureStatus}`,
                },
            }
        );

        check(response, {
                "Unauthorized - expected status": (r) =>
                r.status === failureStatus,
        });

        console.log(
            `ReqRes Unauthorized response: HTTP ${response.status}`
        );
    });
}