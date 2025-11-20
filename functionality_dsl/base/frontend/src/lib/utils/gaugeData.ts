export type GaugeState = {
    value: number;
    connected: boolean;
}

/**
 * Extract numeric gauge value using "path.to.field".
 */
export function extractValue(msg: any, path: string): number | null {
    if (!msg) return null;

    try {
        const v = path.split(".").reduce((acc: any, k: string) =>
            acc == null ? undefined : acc[k], msg);
        const num = Number(v);
        return Number.isFinite(num) ? num : null;
    } catch {
        return null;
    }
}

/**
 * Clamp inside min/max.
 */
export function clamp(val: number, min: number, max: number): number {
    if (!Number.isFinite(val)) return min;
    return Math.min(max, Math.max(min, val));
}
