(() => {
  const controls = {
    protectionEnabled:
      document.getElementById('protection-toggle'),
    notificationsEnabled:
      document.getElementById('notifications-toggle'),
  };

  const threshold = document.getElementById('threshold');
  const saveState = document.getElementById('save-state');
  const error = document.getElementById('error');
  const gmailStatus = document.getElementById('gmail-status');
  const gmailEmail = document.getElementById('gmail-email');
  const gmailAction = document.getElementById('gmail-action');

  function renderSettings(settings) {
    Object.entries(controls).forEach(([key, button]) => {
      const enabled = settings[key];

      button.setAttribute('aria-checked', String(enabled));
      button.classList.toggle('is-on', enabled);
      button.querySelector('.switch-label').textContent =
        enabled ? 'ON' : 'OFF';
    });

    threshold.value = settings.alertThreshold;
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

  function showError(message) {
    error.textContent = message;
    error.hidden = false;
    saveState.textContent = '';
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

  async function save(changes) {
    error.hidden = true;
    saveState.textContent = 'Saving…';

    try {
      renderSettings(
        await MGStorage.updateSettings(changes)
      );
      saveState.textContent = 'Settings saved';
    } catch (errorValue) {
      showError('Could not save settings. Please try again.');
    }
  }

  Object.entries(controls).forEach(([key, button]) => {
    button.addEventListener('click', () => {
      save({
        [key]:
          button.getAttribute('aria-checked') !== 'true',
      });
    });
  });

  threshold.addEventListener('change', () => {
    save({
      alertThreshold: threshold.value,
    });
  });

  gmailAction.addEventListener('click', async () => {
    gmailAction.disabled = true;
    error.hidden = true;

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

  async function load() {
    try {
      const [settings, auth] = await Promise.all([
        MGStorage.ensureDefaults(),
        send('GET_AUTH_STATUS'),
      ]);

      renderSettings(settings);
      renderAuth(auth.auth);
      saveState.textContent =
        'Settings are saved automatically';
    } catch (errorValue) {
      showError(
        'Could not load settings. Please reload this page.'
      );
    }
  }

  if (chrome.storage?.onChanged) {
    chrome.storage.onChanged.addListener(
      (changes, area) => {
        if (
          area === 'local' &&
          changes[MG_CONSTANTS.AUTH_STORAGE_KEY]
        ) {
          send('GET_AUTH_STATUS').then((response) => {
            renderAuth(response.auth);
          });
        }

        if (
          area === 'local' &&
          changes[MG_CONSTANTS.STORAGE_KEY]
        ) {
          MGStorage.getSettings().then(renderSettings);
        }
      }
    );
  }

  load();
})();
