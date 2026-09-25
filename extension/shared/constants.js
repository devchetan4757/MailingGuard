// Shared, phase-safe constants. Gmail and message data are intentionally absent.
const MG_CONSTANTS = Object.freeze({
  STORAGE_KEY: 'mailingGuardSettings',
  DEFAULT_SETTINGS: Object.freeze({
    protectionEnabled: true,
    notificationsEnabled: true,
    alertThreshold: 'high'
  }),
  ALARM_NAME: 'mailingguard-foundation-heartbeat',
  ALARM_PERIOD_MINUTES: 360,
  THRESHOLDS: Object.freeze(['high']),
  SEVERITIES: Object.freeze(['low', 'medium', 'high', 'critical'])
});
