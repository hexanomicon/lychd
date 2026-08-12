import type { AltarStatus } from "./models";

export type CsrfContract = AltarStatus["csrf"];

export function csrfHeadersFromCookie(
  contract: CsrfContract,
  cookieHeader: string
): Record<string, string> {
  const token = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${contract.cookie_name}=`))
    ?.split("=")
    .slice(1)
    .join("=");
  return token
    ? { [contract.header_name]: decodeURIComponent(token) }
    : {};
}
