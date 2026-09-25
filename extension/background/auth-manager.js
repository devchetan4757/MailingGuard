// Explicit, user-initiated OAuth and MailingGuard session lifecycle.
(function () {
  let transientGoogleToken = null;
  function identityToken(options) { return new Promise((resolve, reject) => chrome.identity.getAuthToken(options, (token) => { if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message)); else if (!token) reject(new Error('Google did not return an access token')); else resolve(token); })); }
  function removeCachedToken(token) { if (!token) return Promise.resolve(); return new Promise(resolve => chrome.identity.removeCachedAuthToken({ token }, () => resolve())); }
  async function connect() {
    let token;
    try {
      token = await identityToken({ interactive: true });
      transientGoogleToken = token;
      const profile = await MGGmailClient.getProfile(token);
      const response = await fetch(`${MG_CONSTANTS.BACKEND_BASE_URL}/api/extension/auth`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ accessToken: token }) });
      let body = {}; try { body = await response.json(); } catch (_) { /* handled below */ }
      if (!response.ok || body.authenticated !== true) throw new Error(body.detail || body.error || `MailingGuard authentication failed (${response.status})`);
      if (!safeText(body.email) || body.email.toLowerCase() !== profile.email.toLowerCase() || !safeText(body.sessionToken) || !safeText(body.expiresAt)) throw new Error('MailingGuard returned an invalid verified session');
      const auth = await MGStorage.saveAuth({ connected: true, accountEmail: body.email, mailingGuardSessionToken: body.sessionToken, sessionExpiresAt: body.expiresAt });
      await removeCachedToken(token); transientGoogleToken = null;
      return auth;
    } catch (error) {
      await removeCachedToken(token || transientGoogleToken); transientGoogleToken = null;
      throw normalizeAuthError(error);
    }
  }
  function normalizeAuthError(error) { const message = safeText(error && error.message, 'Gmail authentication failed'); if (/cancel|abort|denied/i.test(message)) return new Error('Google authorization was cancelled.'); if (/Failed to fetch|NetworkError|fetch/i.test(message)) return new Error('MailingGuard could not reach the backend. Check your connection.'); return new Error(message); }
  async function getStatus() { const auth = await MGStorage.ensureAuthState(); if (auth.connected && Date.parse(auth.sessionExpiresAt) <= Date.now()) { await MGStorage.clearAuth(); return { ...MG_CONSTANTS.DEFAULT_AUTH }; } return auth; }
  async function disconnect() { const token = transientGoogleToken || await identityToken({ interactive: false }).catch(() => null); transientGoogleToken = null; await removeCachedToken(token); return MGStorage.clearAuth(); }
  self.MGAuth = Object.freeze({ connect, getStatus, disconnect });
})();
