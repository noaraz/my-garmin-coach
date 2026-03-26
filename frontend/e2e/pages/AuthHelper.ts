/**
 * Generates a test JWT that the AuthContext can decode in the browser.
 *
 * The token is built from plain JSON so the browser's `atob()` can parse it.
 * It is NOT cryptographically signed — tests mock all API calls so the
 * backend never validates this token.
 *
 * Payload fields match AuthContext.decodeJwtPayload / userFromPayload:
 *   userId, email, is_admin, exp
 */
export function makeTestJwt(email = 'test@example.com', userId = 1): string {
  // base64url encode without crypto — works in both Node and browser
  const b64url = (str: string) =>
    Buffer.from(str)
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')

  const header = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = b64url(
    JSON.stringify({
      userId,
      email,
      is_admin: false,
      // Expire 30 days in the future
      exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 30,
    })
  )
  return `${header}.${payload}.fake-e2e-signature`
}

export const TEST_EMAIL = 'test@example.com'
export const TEST_JWT = makeTestJwt(TEST_EMAIL, 1)
