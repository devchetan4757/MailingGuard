(() => {
  const toggle = document.getElementById('protection-toggle');
  const statusText = document.getElementById('status-text');
  const statusDot = document.getElementById('status-dot');
  const help = document.getElementById('protection-help');
  const error = document.getElementById('error');
  const gmailStatus = document.getElementById('gmail-status');
  const gmailEmail = document.getElementById('gmail-email');
  const gmailAction = document.getElementById('gmail-action');

  function showError(message) {
    error.textContent = message;
    error.hidden = false;
  }

  function renderSettings(settings) {
    const enabled = settings.protectionEnabled;

    toggle.setAttribute('aria-checked', String(enabled));
    toggle.classList.toggle('is-on', enabled);
    toggle.querySelector('.switch-label').textContent = enabled
      ? 'ON'
      : 'OFF';

    statusText.textContent = enabled
      ? 'Protected'
      : 'Protection disabled';

    statusDot.classList.toggle('is-off', !enabled);

    help.textContent = enabled
      ? 'Protection is active.'
      : 'Turn protection on to enable it.';
  }

  function renderAuth(auth) {
    const connected = auth.connected === true;

    gmailStatus.textContent = connected
      ? 'Connected'
      : 'Not connected';

    gmailEmail.hidden = !connected;
    gmailEmail.textContent = connected ? auth.accountEmail : '';

    gmailAction.textContent = connected
      ? 'Disconnect Gmail'
      : 'Connect Gmail';

    gmailAction.classList.toggle('danger-button', connected);
  }

  function send(type, changes) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        {
          type,
          changes,
        },
        (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (!response || !response.ok) {
            reject(
              new Error(
                response?.error || 'Request failed'
              )
            );
          } else {
            resolve(response);
          }
        }
      );
    });
  }

  async function load() {
    try {
      const [settings, auth] = await Promise.all([
        MGStorage.ensureDefaults(),
        send('GET_AUTH_STATUS'),
      ]);

      renderSettings(settings);
      renderAuth(auth.auth);
    } catch (errorValue) {
      showError('Could not load settings. Please try again.');
      console.error(errorValue);
    }
  }

  toggle.addEventListener('click', async () => {
    toggle.disabled = true;
    error.hidden = true;

    try {
      renderSettings(
        await MGStorage.updateSettings({
          protectionEnabled:
            toggle.getAttribute('aria-checked') !== 'true',
        })
      );
    } catch (errorValue) {
      showError('Could not save your setting. Please try again.');
    } finally {
      toggle.disabled = false;
    }
  });

  gmailAction.addEventListener('click', async () => {
    gmailAction.disabled = true;
    error.hidden = true;

    gmailStatus.textContent =
      gmailAction.textContent === 'Connect Gmail'
        ? 'Connecting…'
        : 'Disconnecting…';

    try {
      const response = await send(
        gmailAction.textContent === 'Connect Gmail'
          ? 'CONNECT_GMAIL'
          : 'DISCONNECT_GMAIL'
      );

      renderAuth(response.auth);
    } catch (errorValue) {
      showError(errorValue.message);
      await load();
    } finally {
      gmailAction.disabled = false;
    }
  });

  document
    .getElementById('settings-link')
    .addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });

  if (chrome.storage?.onChanged) {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (
        area === 'local' &&
        changes[MG_CONSTANTS.AUTH_STORAGE_KEY]
      ) {
        load();
      }

      if (
        area === 'local' &&
        changes[MG_CONSTANTS.STORAGE_KEY]
      ) {
        MGStorage.getSettings().then(renderSettings);
      }
    });
  }

  load();
})();
