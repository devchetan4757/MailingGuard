// Notification boundary for future analysis results. It never renders authentication details.
(function () {
  function createSuspiciousEmailNotification(input = {}) {
    const title = safeText(input.title, 'Suspicious email detected');
    const severity = normalizeSeverity(input.severity);
    const riskScore = Number.isFinite(Number(input.riskScore)) ? Math.round(Number(input.riskScore)) : null;
    const summary = riskScore === null ? severityLabel(severity) + " - review when ready" : severityLabel(severity) + " - risk score " + riskScore;
    const options = {
      type: 'basic',
      iconUrl: chrome.runtime.getURL('icons/icon128.png'),
      title,
      message: summary,
      priority: severity === 'critical' ? 2 : 1,
      buttons: [{ title: 'Open Email' }, { title: 'Full Analysis' }]
    };
    // detectedSignals are intentionally not included: browser notifications stay concise.
    return new Promise((resolve, reject) => {
      chrome.notifications.create(`mailingguard-${Date.now()}`, options, (id) => {
        if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
        resolve(id);
      });
    });
  }

  self.MGNotifications = Object.freeze({ createSuspiciousEmailNotification });
})();


