// Phase 2.2 configuration. Set the backend URL for the deployment environment.
const MG_CONSTANTS = Object.freeze({
  STORAGE_KEY: 'mailingGuardSettings',
  AUTH_STORAGE_KEY: 'mailingGuardAuth',
  DEFAULT_SETTINGS: Object.freeze({ protectionEnabled: true, notificationsEnabled: true, alertThreshold: 'high' }),
  DEFAULT_AUTH: Object.freeze({ connected: false, accountEmail: '', mailingGuardSessionToken: '', sessionExpiresAt: '' }),
  ALARM_NAME: 'mailingguard-foundation-heartbeat',
  ALARM_PERIOD_MINUTES: 360,
  THRESHOLDS: Object.freeze(['high']),
  SEVERITIES: Object.freeze(['low', 'medium', 'high', 'critical']),
  GMAIL_READONLY_SCOPE: 'https://www.googleapis.com/auth/gmail.readonly',
  // Replace with the deployed MailingGuard API origin. Local development may use http://localhost:8000.
  BACKEND_BASE_URL: 'http://localhost:8000'
});
