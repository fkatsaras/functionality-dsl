export interface ColumnInfo {
    name: string;
    type?: {
        baseType: string;
        format?: string;
        min?: number;
        max?: number;
        exact?: number;
        nullable?: boolean;
    };
}

export function parseErrorDetail(detail: any): string {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail.map((err: any) => {
            if (typeof err === 'string') return err;
            if (err.msg) {
                const field = err.loc?.slice(1).join('.') || '';
                return field ? `${field}: ${err.msg}` : err.msg;
            }
            return JSON.stringify(err);
        }).join(', ');
    }
    if (typeof detail === 'object' && detail !== null) {
        return detail.msg || detail.message || JSON.stringify(detail);
    }
    return String(detail);
}

export function formatValue(value: any, column: ColumnInfo): string {
    if (value === null || value === undefined) {
        return column.type?.nullable ? "null" : "—";
    }

    const typeInfo = column.type;
    if (!typeInfo) return String(value);

    switch (typeInfo.baseType) {
        case "integer":
        case "number":
            if (typeof value === "number") {
                if (typeInfo.baseType === "number") {
                    return value.toFixed(2);
                }
                return String(value);
            }
            return String(value);

        case "boolean":
            return value ? "✓" : "✗";

        case "string":
            if (typeInfo.format) {
                switch (typeInfo.format) {
                    case "date":
                        if (typeof value === "string") {
                            try {
                                const date = new Date(value);
                                return date.toLocaleDateString();
                            } catch {
                                return String(value);
                            }
                        }
                        return String(value);
                    case "time":
                    case "email":
                    case "uri":
                    case "image":
                    default:
                        return String(value);
                }
            }
            return String(value);

        case "array":
            if (Array.isArray(value)) {
                return `[${value.length} items]`;
            }
            return String(value);

        case "object":
            if (typeof value === "object") {
                return "{...}";
            }
            return String(value);

        default:
            return String(value);
    }
}

export function getInputType(fieldName: string, columns: ColumnInfo[]): string {
    const col = columns.find(c => c.name === fieldName);
    if (!col?.type) return "text";

    switch (col.type.baseType) {
        case "integer":
        case "number":
            return "number";
        case "boolean":
            return "checkbox";
        default:
            return "text";
    }
}
