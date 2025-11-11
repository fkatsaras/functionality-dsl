/**
 * Reusable utility for handling path and query parameters in API requests
 */

/**
 * Build a URL by replacing path parameters with values
 * @param template - URL template with {paramName} placeholders
 * @param params - Object with parameter values
 * @returns Built URL or empty string if required params missing
 */
export function buildUrlWithParams(
  template: string,
  params: Record<string, string>
): string {
  let url = template;

  // Find all {paramName} patterns
  const pathParams = template.match(/\{(\w+)\}/g) || [];

  for (const match of pathParams) {
    const paramName = match.slice(1, -1); // Remove { }
    const value = params[paramName];

    if (!value) {
      // Missing required parameter
      return "";
    }

    url = url.replace(match, encodeURIComponent(value));
  }

  return url;
}

/**
 * Extract path parameter names from a URL template
 * @param template - URL template with {paramName} placeholders
 * @returns Array of parameter names
 */
export function extractPathParams(template: string): string[] {
  const matches = template.match(/\{(\w+)\}/g) || [];
  return matches.map(m => m.slice(1, -1));
}

/**
 * Check if all required parameters have values
 * @param params - Parameter names
 * @param values - Parameter values object
 * @returns true if all params have non-empty values
 */
export function allParamsFilled(
  params: string[],
  values: Record<string, string>
): boolean {
  return params.every(p => values[p] && values[p].trim() !== "");
}

/**
 * Build query string from parameter values
 * @param params - Query parameter values
 * @returns URL query string (without leading ?)
 */
export function buildQueryString(params: Record<string, string>): string {
  return Object.entries(params)
    .filter(([_, value]) => value.trim() !== "")
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join("&");
}
