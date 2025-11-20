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
 */
export function detectKeys(row: any) {
    const keys = Object.keys(row);
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
    if (value == null || xMeta == null) return null;

    // ---------------------------
    // numeric types
    // ---------------------------
    if (xMeta.type === "number" || xMeta.type === "integer") {
        // int / float / int64 / double → numeric timestamp
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
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

        // string <date_time>
        if (xMeta.format === "date_time") {
            const t = Date.parse(value);
            return Number.isNaN(t) ? null : t;
        }

        // generic string → not usable as axis
        return null;
    }

    return null;
}
