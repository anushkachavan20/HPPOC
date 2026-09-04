import http from "k6/http";
import { check, group } from "k6";

/*
 * Service 1: JSONPlaceholder
 *
 * Purpose:
 * - Use real public APIs
 * - GET requests only
 * - No fake request data
 * - No POST / PUT / DELETE
 * - Generate successful and failure scenarios
 *
 * The Python parser determines the final PASS/FAIL status
 * from the HTTP status code:
 *
 * 2xx / 3xx -> PASS
 * 4xx / 5xx -> FAIL
 */

export const options = {
    vus: 1,
    iterations: 1,
};

const BASE_URL = "https://jsonplaceholder.typicode.com";
const failureScenario = __ENV.FAIL_SCENARIO || "none";

export default function () {

    // =========================================================
    // API 1 - Get all posts
    // Expected HTTP status: 200
    // =========================================================

    group("JSONPlaceholder Service - GetPosts", function () {

        const response = http.get(
            `${BASE_URL}/posts`,
            {
                tags: {
                    service: "jsonplaceholder",
                    test: "GetPosts",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "GetPosts - HTTP 200": (r) =>
                r.status === 200,
        });
    });

    // =========================================================
    // API 2 - Get a specific post
    // Expected HTTP status: 200
    // =========================================================

    group("JSONPlaceholder Service - GetPost", function () {

        const response = http.get(
            `${BASE_URL}/posts/1`,
            {
                tags: {
                    service: "jsonplaceholder",
                    test: "GetPost",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "GetPost - HTTP 200": (r) =>
                r.status === 200,
        });
    });

    // =========================================================
    // API 3 - Intentionally request a non-existent resource
    //
    // Expected HTTP status: 404
    //
    // This is an intentional failure scenario for the POC.
    // No data is created, modified, or deleted.
    // =========================================================

    group("JSONPlaceholder Service - NotFound", function () {

        const failureStatus = ["401", "404", "500"].includes(failureScenario)
            ? Number(failureScenario)
            : 200;
        const expectedStatus = failureStatus;
        const requestUrl = failureStatus === 200
            ? `${BASE_URL}/posts/1`
            : `https://httpbin.org/status/${failureStatus}`;
        const response = http.get(
            requestUrl,
            {
                tags: {
                    service: "jsonplaceholder",
                    test: "NotFound",
                    expected_status: String(expectedStatus),
                    failure_type: failureStatus === 200 ? "none" : `http_${failureStatus}`,
                },
            }
        );

        check(response, {
                "NotFound - expected status": (r) =>
                r.status === expectedStatus,
        });

        console.log(
            `JSONPlaceholder NotFound response: HTTP ${response.status}`
        );
    });
}