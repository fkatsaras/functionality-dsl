// --------------------------------------
// Shared Chart Normalization Utilities
// --------------------------------------

export type Point = { t: number; y: number };

export interface NormalizedChartData {
    xKey: string | null;
    yKeys: string[];
    series: Record<string, Point[]>;
}

/**
 * Detect keys from the first row.
 * The 1st key becomes the X axis.
 * The rest of the keys become Y series.
 * Filters out arrays, objects, and metadata keys.
 */
export function detectKeys(row: any) {
    // Filter out metadata keys and non-primitive values (arrays, objects)
    const keys = Object.keys(row).filter(k => {
        if (k.startsWith('__')) return false;
        const val = row[k];
        // Only allow primitives (string, number, boolean, null)
        return val === null || typeof val !== 'object';
    });

    if (keys.length === 0) {
        return { xKey: null, yKeys: [], series: {} };
    }

    const xKey = keys[0];
    const yKeys = keys.slice(1);

    const series = Object.fromEntries(
        yKeys.map(k => [k, [] as Point[]])
    );

    return { xKey, yKeys, series };
}


/**
 * Push one row into the normalized structure.
 */
export function pushRow(
    row: any,
    xKey: string,
    yKeys: string[],
    series: Record<string, Point[]>,
    windowSize: number | undefined,
    xMeta: any
) {
    const t = normalizeX(row[xKey], xMeta);
    if (t == null) return series;

    const next = { ...series };

    for (const key of yKeys) {
        const y = Number(row[key]);
        if (!Number.isFinite(y)) continue;

        const arr = [...(next[key] ?? []), { t, y }];
        next[key] = windowSize ? arr.slice(-windowSize) : arr;
    }

    return next;
}


export function normalizeX(value: any, xMeta: any): number | null {
    if (value == null) return null;

    // If no metadata, try to auto-detect
    if (xMeta == null) {
        // Try parsing as date string
        if (typeof value === "string") {
            const t = Date.parse(value);
            if (!Number.isNaN(t)) return t;
        }
        // Try parsing as number
        const n = Number(value);
        if (Number.isFinite(n)) return n;
        return null;
    }

    // ---------------------------
    // numeric types
    // ---------------------------
    if (xMeta.type === "number" || xMeta.type === "integer") {
        const n = Number(value);
        if (!Number.isFinite(n)) return null;

        // If xMeta has datetime format, treat as Unix timestamp in seconds
        // and convert to milliseconds for JavaScript
        if (xMeta.format === "datetime" || xMeta.format === "date_time") {
            return n * 1000;
        }

        // Otherwise, use as-is
        return n;
    }

    // ---------------------------
    // string types
    // ---------------------------
    if (xMeta.type === "string") {

        // string <date>
        if (xMeta.format === "date") {
            const t = Date.parse(value);
            return Number.isNaN(t) ? null : t;
        }

        // string <date_time> or <datetime>
        if (xMeta.format === "date_time" || xMeta.format === "datetime") {
            const t = Date.parse(value);
            return Number.isNaN(t) ? null : t;
        }

        // string <time>
        if (xMeta.format === "time") {
            const t = Date.parse(value);
            return Number.isNaN(t) ? null : t;
        }

        // generic string -> not usable as axis
        return null;
    }

    return null;
}
