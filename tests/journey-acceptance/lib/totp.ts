// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 Identity, Secrets And Authority (T2 OTP step-up)
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { createHmac, randomBytes } from "node:crypto";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function base32Encode(bytes: Uint8Array): string {
  let bits = 0;
  let value = 0;
  let output = "";
  for (const byte of bytes) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      output += ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) {
    output += ALPHABET[(value << (5 - bits)) & 31];
  }
  return output;
}

export function base32Decode(text: string): Buffer {
  let bits = 0;
  let value = 0;
  const bytes: number[] = [];
  for (const char of text.replace(/=+$/u, "").toUpperCase()) {
    const index = ALPHABET.indexOf(char);
    if (index === -1) {
      throw new Error("not a base32 string");
    }
    value = (value << 5) | index;
    bits += 5;
    if (bits >= 8) {
      bytes.push((value >>> (bits - 8)) & 255);
      bits -= 8;
    }
  }
  return Buffer.from(bytes);
}

export function generateOtpSecret(): string {
  return base32Encode(randomBytes(20));
}

/** RFC 6238 time-based one-time password (HMAC-SHA1, 6 digits, 30 second period), matching Keycloak's default OTP policy. */
export function totp(secretBase32: string, nowMs: number, digits = 6, periodSeconds = 30): string {
  const counter = Math.floor(nowMs / 1000 / periodSeconds);
  const message = Buffer.alloc(8);
  message.writeBigUInt64BE(BigInt(counter));
  const hmac = createHmac("sha1", base32Decode(secretBase32)).update(message).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const code = ((hmac[offset] & 0x7f) << 24) | (hmac[offset + 1] << 16) | (hmac[offset + 2] << 8) | hmac[offset + 3];
  return String(code % 10 ** digits).padStart(digits, "0");
}
