// Small Gmail client used only to identify the account after explicit OAuth consent.
(function () {
  const PROFILE_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/profile';
  async function getProfile(accessToken) {
    if (!safeText(accessToken)) throw new Error('Missing Google access token');
    const response = await fetch(PROFILE_URL, { headers: { Authorization: `Bearer ${accessToken}` } });
    if (response.status === 401) throw new Error('Google access token is invalid or expired');
    if (!response.ok) throw new Error(`Gmail account lookup failed (${response.status})`);
    const profile = await response.json();
    if (!safeText(profile.emailAddress)) throw new Error('Google did not return an account email');
    return { email: profile.emailAddress };
  }
  self.MGGmailClient = Object.freeze({ getProfile });
})();
