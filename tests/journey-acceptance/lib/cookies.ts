// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W2 Platform (one-use hand-off cookie)
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

export interface ParsedCookie {
  name: string;
  value: string;
  httpOnly: boolean;
  secure: boolean;
  sameSite: string;
  path: string;
}

/** Reads one cookie from a raw Set-Cookie header value; several cookies arrive separated by newlines. */
export function parseSetCookie(raw: string, name: string): ParsedCookie | undefined {
  for (const line of raw.split("\n")) {
    const [pair, ...attributes] = line.split(";").map((part) => part.trim());
    const separator = pair.indexOf("=");
    if (separator === -1 || pair.slice(0, separator) !== name) {
      continue;
    }
    const lower = attributes.map((attribute) => attribute.toLowerCase());
    const attribute = (key: string): string => lower.find((item) => item.startsWith(`${key}=`))?.slice(key.length + 1) ?? "";
    return {
      name,
      value: pair.slice(separator + 1),
      httpOnly: lower.includes("httponly"),
      secure: lower.includes("secure"),
      sameSite: attribute("samesite"),
      path: attributes.find((item) => item.toLowerCase().startsWith("path="))?.slice(5) ?? "",
    };
  }
  return undefined;
}
