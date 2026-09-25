importScripts(
  '../shared/constants.js',
  '../shared/risk.js',
  '../shared/utils.js',
  'storage.js',
  'gmail-client.js',
  'auth-manager.js',
  'notification-manager.js'
);

async function initializeFoundation() {
  try {
    await MGStorage.ensureDefaults();
    await MGStorage.ensureAuthState();
    await chrome.alarms.create(
      MG_CONSTANTS.ALARM_NAME,
      { periodInMinutes: MG_CONSTANTS.ALARM_PERIOD_MINUTES }
    );
  } catch (error) {
    console.error('MailingGuard foundation initialization failed:', error);
  }
}

chrome.runtime.onInstalled.addListener(() => {
  initializeFoundation();
});

chrome.runtime.onStartup.addListener(() => {
  initializeFoundation();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === MG_CONSTANTS.ALARM_NAME) {
    initializeFoundation();
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    if (!message || typeof message.type !== 'string') {
      throw new Error('Invalid message');
    }

    if (message.type === 'GET_SETTINGS') {
      return {
        ok: true,
        settings: await MGStorage.ensureDefaults(),
      };
    }

    if (message.type === 'UPDATE_SETTINGS') {
      return {
        ok: true,
        settings: await MGStorage.updateSettings(message.changes),
      };
    }

    if (message.type === 'GET_AUTH_STATUS') {
      return {
        ok: true,
        auth: await MGAuth.getStatus(),
      };
    }

    if (message.type === 'CONNECT_GMAIL') {
      return {
        ok: true,
        auth: await MGAuth.connect(),
      };
    }

    if (message.type === 'DISCONNECT_GMAIL') {
      return {
        ok: true,
        auth: await MGAuth.disconnect(),
      };
    }

    if (message.type === 'TEST_NOTIFICATION') {
      await MGNotifications.createSuspiciousEmailNotification({
        title: 'MailingGuard test notification',
        severity: 'high',
        riskScore: 80,
      });
      return { ok: true };
    }

    throw new Error('Unknown message type');
  })()
    .then(sendResponse)
    .catch((error) => {
      sendResponse({
        ok: false,
        error: error.message,
      });
    });

  return true;
});

chrome.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {
  console.info(
    'MailingGuard notification action:',
    notificationId,
    buttonIndex
  );
});
