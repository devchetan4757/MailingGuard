(() => {
  const toggle = document.getElementById('protection-toggle');
  const statusText = document.getElementById('status-text');
  const statusDot = document.getElementById('status-dot');
  const help = document.getElementById('protection-help');
  const error = document.getElementById('error');

  function showError(message) { error.textContent = message; error.hidden = false; }
  function render(settings) {
    const enabled = settings.protectionEnabled;
    toggle.setAttribute('aria-checked', String(enabled));
    toggle.classList.toggle('is-on', enabled);
    toggle.querySelector('.switch-label').textContent = enabled ? 'ON' : 'OFF';
    statusText.textContent = enabled ? 'Protected' : 'Protection disabled';
    statusDot.classList.toggle('is-off', !enabled);
    help.textContent = enabled ? 'Protection is active.' : 'Turn protection on to enable it.';
  }
  async function load() {
    try { render(await MGStorage.ensureDefaults()); }
    catch (e) { showError('Settings could not be loaded. Please try again.'); console.error(e); }
  }
  toggle.addEventListener('click', async () => {
    toggle.disabled = true; error.hidden = true;
    try { render(await MGStorage.updateSettings({ protectionEnabled: toggle.getAttribute('aria-checked') !== 'true' })); }
    catch (e) { showError('Could not save your setting. Please try again.'); console.error(e); }
    finally { toggle.disabled = false; }
  });
  document.getElementById('settings-link').addEventListener('click', () => chrome.runtime.openOptionsPage());
  if (chrome.storage?.onChanged) chrome.storage.onChanged.addListener((changes, area) => { if (area === 'local' && changes[MG_CONSTANTS.STORAGE_KEY]) load(); });
  load();
})();
