/**
 * HttpClient — fetch-based HTTP with Basic Auth.
 *
 * All methods return parsed JSON. Throws RestError on non-2xx responses.
 * Returns {} on 204 No Content.
 */
import type { HttpClientOptions, QueryParams } from './types.js';
/**
 * Low-level HTTP client used by every REST namespace resource.
 *
 * Handles Basic Auth, JSON encoding/decoding, and error normalisation
 * ({@link RestError} on non-2xx). Normally you do not instantiate this
 * directly — construct a {@link RestClient} instead.
 */
export declare class HttpClient {
    /** Fully-qualified base URL (no trailing slash). */
    readonly baseUrl: string;
    private readonly _authHeader;
    private readonly _fetch;
    /**
     * Build a new HTTP client.
     *
     * @param options - Connection options. Either `host` (bare hostname;
     *   `https://` is prepended automatically) or `baseUrl` (fully-qualified)
     *   must be provided along with `project` + `token`.
     * @throws {Error} When neither `host` nor `baseUrl` is supplied.
     */
    constructor(options: HttpClientOptions);
    private _request;
    /**
     * Perform an authenticated HTTP GET and return the parsed JSON response.
     *
     * @typeParam T - Expected response body type.
     * @param path - Absolute URL or path relative to {@link HttpClient.baseUrl}.
     * @param params - Optional query parameters; `undefined` values are skipped.
     * @returns The parsed JSON body, or `{}` on `204 No Content`.
     * @throws {RestError} On any non-2xx HTTP response.
     */
    get<T = any>(path: string, params?: QueryParams): Promise<T>;
    /**
     * Perform an authenticated HTTP POST and return the parsed JSON response.
     *
     * @typeParam T - Expected response body type.
     * @param path - Absolute URL or path relative to {@link HttpClient.baseUrl}.
     * @param body - JSON-serialisable request body. Omit to send no body.
     * @param params - Optional query parameters appended to the URL.
     * @returns The parsed JSON body, or `{}` on `204 No Content`.
     * @throws {RestError} On any non-2xx HTTP response.
     */
    post<T = any>(path: string, body?: any, params?: QueryParams): Promise<T>;
    /**
     * Perform an authenticated HTTP PUT and return the parsed JSON response.
     *
     * @typeParam T - Expected response body type.
     * @param path - Absolute URL or path relative to {@link HttpClient.baseUrl}.
     * @param body - JSON-serialisable request body.
     * @returns The parsed JSON body, or `{}` on `204 No Content`.
     * @throws {RestError} On any non-2xx HTTP response.
     */
    put<T = any>(path: string, body?: any): Promise<T>;
    /**
     * Perform an authenticated HTTP PATCH and return the parsed JSON response.
     *
     * @typeParam T - Expected response body type.
     * @param path - Absolute URL or path relative to {@link HttpClient.baseUrl}.
     * @param body - JSON-serialisable partial request body.
     * @returns The parsed JSON body, or `{}` on `204 No Content`.
     * @throws {RestError} On any non-2xx HTTP response.
     */
    patch<T = any>(path: string, body?: any): Promise<T>;
    /**
     * Perform an authenticated HTTP DELETE and return the parsed JSON response.
     *
     * @typeParam T - Expected response body type.
     * @param path - Absolute URL or path relative to {@link HttpClient.baseUrl}.
     * @returns The parsed JSON body, or `{}` on `204 No Content`.
     * @throws {RestError} On any non-2xx HTTP response.
     */
    delete<T = any>(path: string): Promise<T>;
}
