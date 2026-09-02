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

export default function () {

    // =========================================================
    // API 1 - Basic GET
    //
    // Expected: 200
    // =========================================================

    group("HTTPBin Service - Get", function () {

        const response = http.get(
            `${BASE_URL}/get`,
            {
                tags: {
                    service: "httpbin",
                    test: "Get",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "Get - HTTP 200": (r) =>
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

    group("HTTPBin Service - UUID", function () {

        const response = http.get(
            `${BASE_URL}/uuid`,
            {
                tags: {
                    service: "httpbin",
                    test: "UUID",
                    expected_status: "200",
                },
            }
        );

        check(response, {
            "UUID - HTTP 200": (r) =>
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

    group("HTTPBin Service - ServerError", function () {

        const response = http.get(
            `${BASE_URL}/status/500`,
            {
                tags: {
                    service: "httpbin",
                    test: "ServerError",
                    expected_status: "500",
                    failure_type: "server_error",
                },
            }
        );

        check(response, {
            "ServerError - HTTP 500": (r) =>
                r.status === 500,
        });

        console.log(
            `HTTPBin ServerError response: HTTP ${response.status}`
        );
    });
}