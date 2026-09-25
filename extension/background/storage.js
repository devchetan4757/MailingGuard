// The single storage abstraction used by the popup, options page, and worker.
(function () {
  const defaults = { ...MG_CONSTANTS.DEFAULT_SETTINGS };

  function readRaw() {
    return new Promise((resolve, reject) => {
      chrome.storage.local.get(MG_CONSTANTS.STORAGE_KEY, (result) => {
        if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
        resolve(result[MG_CONSTANTS.STORAGE_KEY]);
      });
    });
  }

  function writeRaw(settings) {
    return new Promise((resolve, reject) => {
      chrome.storage.local.set({ [MG_CONSTANTS.STORAGE_KEY]: settings }, () => {
        if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
        resolve(settings);
      });
    });
  }

  function sanitize(value) {
    const source = isPlainObject(value) ? value : {};
    return {
      protectionEnabled: typeof source.protectionEnabled === 'boolean' ? source.protectionEnabled : defaults.protectionEnabled,
      notificationsEnabled: typeof source.notificationsEnabled === 'boolean' ? source.notificationsEnabled : defaults.notificationsEnabled,
      alertThreshold: MG_CONSTANTS.THRESHOLDS.includes(source.alertThreshold) ? source.alertThreshold : defaults.alertThreshold
    };
  }

  async function ensureDefaults() {
    const current = sanitize(await readRaw());
    const existing = await readRaw();
    if (!isPlainObject(existing) || JSON.stringify(existing) !== JSON.stringify(current)) await writeRaw(current);
    return current;
  }

  async function getSettings() { return sanitize(await readRaw()); }
  async function updateSettings(changes) {
    const updated = { ...(await getSettings()), ...(isPlainObject(changes) ? changes : {}) };
    const safe = sanitize(updated);
    return writeRaw(safe);
  }

  self.MGStorage = Object.freeze({ ensureDefaults, getSettings, updateSettings, defaults: { ...defaults } });
})();
