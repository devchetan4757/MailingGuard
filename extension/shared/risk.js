// Helpers only. Authoritative email scoring remains in the backend.
function normalizeSeverity(value) {
  const severity = String(value || '').toLowerCase();
  return MG_CONSTANTS.SEVERITIES.includes(severity) ? severity : 'high';
}

function severityLabel(value) {
  const labels = { low: 'Low risk', medium: 'Medium risk', high: 'High risk', critical: 'Critical risk' };
  return labels[normalizeSeverity(value)];
}

function meetsAlertThreshold(severity, threshold) {
  const order = { low: 0, medium: 1, high: 2, critical: 3 };
  const normalizedThreshold = MG_CONSTANTS.THRESHOLDS.includes(threshold) ? threshold : 'high';
  return order[normalizeSeverity(severity)] >= order[normalizedThreshold];
}
