(() => {
  const controls = { protectionEnabled: document.getElementById('protection-toggle'), notificationsEnabled: document.getElementById('notifications-toggle') };
  const threshold = document.getElementById('threshold'); const saveState = document.getElementById('save-state'); const error = document.getElementById('error');
  function render(settings) { Object.entries(controls).forEach(([key, button]) => { const on = settings[key]; button.setAttribute('aria-checked', String(on)); button.classList.toggle('is-on', on); button.querySelector('.switch-label').textContent = on ? 'ON' : 'OFF'; }); threshold.value = settings.alertThreshold; }
  function showError(message) { error.textContent = message; error.hidden = false; saveState.textContent = ''; }
  async function save(changes) { error.hidden = true; saveState.textContent = 'Saving...'; try { render(await MGStorage.updateSettings(changes)); saveState.textContent = 'Settings saved'; } catch (e) { showError('Could not save settings. Please try again.'); console.error(e); } }
  Object.entries(controls).forEach(([key, button]) => button.addEventListener('click', () => save({ [key]: button.getAttribute('aria-checked') !== 'true' })));
  threshold.addEventListener('change', () => save({ alertThreshold: threshold.value }));
  if (chrome.storage?.onChanged) chrome.storage.onChanged.addListener((changes, area) => { if (area === 'local' && changes[MG_CONSTANTS.STORAGE_KEY]) { render(changes[MG_CONSTANTS.STORAGE_KEY].newValue); saveState.textContent = 'Settings updated'; } });
  MGStorage.ensureDefaults().then(render).then(() => { saveState.textContent = 'Settings are saved automatically'; }).catch((e) => { showError('Settings could not be loaded. Please reload this page.'); console.error(e); });
})();


