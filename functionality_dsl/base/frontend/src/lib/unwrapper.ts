export interface EntityResponse<T = any> {
  columns: string[];  // ordered column/attribute names
  rows: T[];  // array of objects
}




/**
 * Normalize backend entity response into an array of rows
 *
 * Handles:
 *   - [{ "fieldName": [...] }] -> [...]
 *   - { "fieldName": [...] }   -> [...]
 *   - already an array  -> [...]
 */
export function unwrapEntityResponse<T = any>(json: any): T[] {
  if (Array.isArray(json)) {
    if (
      json.length === 1 &&
      typeof json[0] === "object" &&
      Object.keys(json[0]).length === 1
    ) {
      const firstKey = Object.keys(json[0])[0];
      const unwrapped = json[0][firstKey];
      if (Array.isArray(unwrapped)) return unwrapped;
      return [unwrapped];
    }
  } else if (json && typeof json === "object") {
    if (Array.isArray(json.rows)) return json.rows;
  }
  throw new Error("Unexpected response format.");
}