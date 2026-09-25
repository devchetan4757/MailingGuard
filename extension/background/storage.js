// The single storage abstraction used by the popup, options page, and worker.
(function () {
  const settingsDefaults = {
    ...MG_CONSTANTS.DEFAULT_SETTINGS,
  };

  const authDefaults = {
    ...MG_CONSTANTS.DEFAULT_AUTH,
  };

  function getRaw(key) {
    return new Promise((resolve, reject) => {
      chrome.storage.local.get(key, (result) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(result[key]);
        }
      });
    });
  }

  function setRaw(key, value) {
    return new Promise((resolve, reject) => {
      chrome.storage.local.set({ [key]: value }, () => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(value);
        }
      });
    });
  }

  function sanitizeSettings(value) {
    const source = isPlainObject(value) ? value : {};

    return {
      protectionEnabled:
        typeof source.protectionEnabled === 'boolean'
          ? source.protectionEnabled
          : true,
      notificationsEnabled:
        typeof source.notificationsEnabled === 'boolean'
          ? source.notificationsEnabled
          : true,
      alertThreshold: MG_CONSTANTS.THRESHOLDS.includes(source.alertThreshold)
        ? source.alertThreshold
        : 'high',
    };
  }

  function sanitizeAuth(value) {
    const source = isPlainObject(value) ? value : {};
    const expires = safeText(source.sessionExpiresAt);

    const connected =
      source.connected === true &&
      safeText(source.accountEmail) !== '' &&
      safeText(source.mailingGuardSessionToken) !== '' &&
      expires !== '' &&
      Date.parse(expires) > Date.now();

    return {
      connected,
      accountEmail: connected ? safeText(source.accountEmail) : '',
      mailingGuardSessionToken: connected
        ? safeText(source.mailingGuardSessionToken)
        : '',
      sessionExpiresAt: connected ? expires : '',
    };
  }

  async function ensureDefaults() {
    const existing = await getRaw(MG_CONSTANTS.STORAGE_KEY);
    const settings = sanitizeSettings(existing);

    if (JSON.stringify(existing) !== JSON.stringify(settings)) {
      await setRaw(MG_CONSTANTS.STORAGE_KEY, settings);
    }

    return settings;
  }

  async function getSettings() {
    return sanitizeSettings(await getRaw(MG_CONSTANTS.STORAGE_KEY));
  }

  async function updateSettings(changes) {
    return setRaw(
      MG_CONSTANTS.STORAGE_KEY,
      sanitizeSettings({
        ...(await getSettings()),
        ...(isPlainObject(changes) ? changes : {}),
      })
    );
  }

  async function getAuth() {
    return sanitizeAuth(await getRaw(MG_CONSTANTS.AUTH_STORAGE_KEY));
  }

  async function saveAuth(auth) {
    const safe = sanitizeAuth({
      ...auth,
      connected: true,
    });

    if (!safe.connected) {
      throw new Error('Invalid or expired MailingGuard session');
    }

    return setRaw(MG_CONSTANTS.AUTH_STORAGE_KEY, safe);
  }

  async function clearAuth() {
    return setRaw(MG_CONSTANTS.AUTH_STORAGE_KEY, {
      ...authDefaults,
    });
  }

  async function ensureAuthState() {
    const existing = await getRaw(MG_CONSTANTS.AUTH_STORAGE_KEY);
    const auth = sanitizeAuth(existing);

    if (JSON.stringify(existing) !== JSON.stringify(auth)) {
      await setRaw(MG_CONSTANTS.AUTH_STORAGE_KEY, auth);
    }

    return auth;
  }

  self.MGStorage = Object.freeze({
    ensureDefaults,
    getSettings,
    updateSettings,
    getAuth,
    saveAuth,
    clearAuth,
    ensureAuthState,
    settingsDefaults: { ...settingsDefaults },
    authDefaults: { ...authDefaults },
  });
})();
