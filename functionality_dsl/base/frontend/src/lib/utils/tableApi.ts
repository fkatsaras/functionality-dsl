import { parseErrorDetail } from './tableFormat';

export interface AuthConfig {
    authType: string;
    authToken: string | null;
}

export interface LoadResult {
    data: any[];
    entityData: Record<string, any> | null;
    entityKeys: string[];
    isPermissionError: boolean;
    error: string | null;
}

export interface MutateResult {
    isPermissionError: boolean;
    error: string | null;
}

export interface CreateResult extends MutateResult {
    fieldErrors: Record<string, string>;
    success: boolean;
}

export function buildAuthHeaders(auth: AuthConfig): { headers: Record<string, string>; fetchOptions: RequestInit } {
    const headers: Record<string, string> = {};
    const fetchOptions: RequestInit = { headers };

    if (auth.authType === 'jwt' && auth.authToken) {
        headers['Authorization'] = `Bearer ${auth.authToken}`;
    } else if (auth.authType === 'basic' && auth.authToken) {
        headers['Authorization'] = `Basic ${auth.authToken}`;
    } else if (auth.authType === 'session') {
        fetchOptions.credentials = 'include';
    }

    return { headers, fetchOptions };
}

export async function loadTableData(
    url: string,
    auth: AuthConfig,
    itemMode: boolean,
    arrayField: string | null,
): Promise<LoadResult> {
    const { headers, fetchOptions } = buildAuthHeaders(auth);

    const response = await fetch(url, { ...fetchOptions, headers });

    if (!response.ok) {
        if (response.status === 403) {
            const errBody = await response.json().catch(() => ({ detail: "Forbidden" }));
            return {
                data: [], entityData: null, entityKeys: [],
                isPermissionError: true,
                error: errBody.detail || "You don't have permission to view this data",
            };
        }
        return {
            data: [], entityData: null, entityKeys: [],
            isPermissionError: false,
            error: `${response.status} ${response.statusText}`,
        };
    }

    const json = await response.json();

    if (itemMode && arrayField) {
        const data = json[arrayField] || [];
        const entityKeys = data.length > 0 && typeof data[0] === "object" ? Object.keys(data[0]) : [];
        return { data, entityData: json, entityKeys, isPermissionError: false, error: null };
    }

    // Entity mode: heuristic extraction
    let data: any[] = [];
    if (Array.isArray(json)) {
        if (json.length === 1 && typeof json[0] === "object" && Object.keys(json[0]).length === 1) {
            const firstKey = Object.keys(json[0])[0];
            data = json[0][firstKey];
        } else {
            data = json;
        }
    } else if (json && typeof json === "object") {
        const keys = Object.keys(json);
        if (keys.length === 1) {
            const first = json[keys[0]];
            if (Array.isArray(first)) {
                data = first;
            } else if (first && typeof first === "object") {
                const innerKeys = Object.keys(first);
                if (innerKeys.length === 1 && Array.isArray(first[innerKeys[0]])) {
                    data = first[innerKeys[0]];
                } else {
                    throw new Error("Expected object with single array field inside entity.");
                }
            } else {
                throw new Error("Expected entity object or array.");
            }
        } else {
            const arrayKey = keys.find(k => Array.isArray(json[k]));
            if (arrayKey) {
                data = json[arrayKey];
            } else {
                throw new Error("Expected single entity key or an object with an array field.");
            }
        }
    }

    const entityKeys = data.length > 0 && typeof data[0] === "object" ? Object.keys(data[0]) : [];
    return { data, entityData: null, entityKeys, isPermissionError: false, error: null };
}

export async function saveRow(
    url: string,
    auth: AuthConfig,
    editData: Record<string, any>,
    itemMode: boolean,
    arrayField: string | null,
    entityData: Record<string, any> | null,
    allData: any[],
    rowIndex: number,
): Promise<MutateResult> {
    const { headers, fetchOptions } = buildAuthHeaders(auth);
    headers['Content-Type'] = 'application/json';

    let payload: any;
    if (itemMode && arrayField && entityData) {
        const updatedItems = [...allData];
        updatedItems[rowIndex] = editData;
        payload = { ...entityData, [arrayField]: updatedItems };
    } else {
        payload = editData;
    }

    const response = await fetch(url, { ...fetchOptions, method: 'PUT', headers, body: JSON.stringify(payload) });

    if (!response.ok) {
        const errBody = await response.json().catch(() => ({ detail: response.statusText }));
        const errorDetail = parseErrorDetail(errBody.detail);
        if (response.status === 403) {
            return { isPermissionError: true, error: errorDetail || "You don't have permission to update items" };
        }
        return { isPermissionError: false, error: errorDetail || `HTTP ${response.status}` };
    }

    return { isPermissionError: false, error: null };
}

export async function createRow(
    url: string,
    auth: AuthConfig,
    formData: Record<string, any>,
    editableFields: string[],
    itemMode: boolean,
    arrayField: string | null,
    entityData: Record<string, any> | null,
    allData: any[],
): Promise<CreateResult> {
    const { headers, fetchOptions } = buildAuthHeaders(auth);
    headers['Content-Type'] = 'application/json';

    let method: string;
    let payload: any;

    if (itemMode && arrayField && entityData) {
        payload = { ...entityData, [arrayField]: [...allData, formData] };
        method = 'PUT';
    } else {
        payload = formData;
        method = 'POST';
    }

    const response = await fetch(url, { ...fetchOptions, method, headers, body: JSON.stringify(payload) });

    if (!response.ok) {
        const errBody = await response.json().catch(() => ({ detail: response.statusText }));

        if (response.status === 403) {
            return {
                isPermissionError: true,
                error: parseErrorDetail(errBody.detail) || "You don't have permission to create items",
                fieldErrors: {},
                success: false,
            };
        }

        if (Array.isArray(errBody.detail)) {
            const fieldErrs: Record<string, string> = {};
            const formErrs: string[] = [];
            for (const err of errBody.detail) {
                const fieldKey = err.loc
                    ? [...err.loc].reverse().find((s: any) => typeof s === 'string' && s !== 'body')
                    : null;
                if (fieldKey && editableFields.includes(fieldKey)) {
                    fieldErrs[fieldKey] = err.msg ?? 'Invalid value';
                } else {
                    formErrs.push(err.msg ?? JSON.stringify(err));
                }
            }
            return {
                isPermissionError: false,
                error: formErrs.length > 0 ? formErrs.join(', ') : null,
                fieldErrors: fieldErrs,
                success: false,
            };
        }

        return {
            isPermissionError: false,
            error: parseErrorDetail(errBody.detail) || `HTTP ${response.status}`,
            fieldErrors: {},
            success: false,
        };
    }

    return { isPermissionError: false, error: null, fieldErrors: {}, success: true };
}

export async function deleteRow(
    url: string,
    auth: AuthConfig,
    rowIndex: number,
    itemMode: boolean,
    arrayField: string | null,
    entityData: Record<string, any> | null,
    allData: any[],
): Promise<MutateResult> {
    const { headers, fetchOptions } = buildAuthHeaders(auth);
    headers['Content-Type'] = 'application/json';

    let method: string;
    let payload: any;

    if (itemMode && arrayField && entityData) {
        const updatedItems = allData.filter((_, idx) => idx !== rowIndex);
        payload = { ...entityData, [arrayField]: updatedItems };
        method = 'PUT';
    } else {
        payload = allData[rowIndex];
        method = 'DELETE';
    }

    const response = await fetch(url, { ...fetchOptions, method, headers, body: JSON.stringify(payload) });

    if (!response.ok) {
        const errBody = await response.json().catch(() => ({ detail: response.statusText }));
        const errorDetail = parseErrorDetail(errBody.detail);
        if (response.status === 403) {
            return { isPermissionError: true, error: errorDetail || "You don't have permission to delete items" };
        }
        return { isPermissionError: false, error: errorDetail || `HTTP ${response.status}` };
    }

    return { isPermissionError: false, error: null };
}
