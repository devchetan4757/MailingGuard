/* -------------------------------------------------------------------------- */
/* Dashboard visual tokens                                                     */
/* -------------------------------------------------------------------------- */
/*
 * Palette direction: "signal in the dark" — a near-black navy void (the
 * inbox at rest) pierced by an electric cyan detection pulse. Violet marks
 * anything the model itself is telling you (vs. raw counts), and threat
 * severity stays on a red -> amber -> emerald scale so risk is legible at
 * a glance, independent of the brand accent.
 */

export const COLORS = {
  canvas: "#070A13",
  card: "#0D1220",
  elevated: "#131A2D",
  border: "#1E2740",
  borderStrong: "#2B3555",
  grid: "#1E2740",

  text: "#EAEEF9",
  secondary: "#8791AD",
  muted: "#525C7A",

  // Main UI / detection accent
  accent: "#2FE0FF",
  accentMuted: "#155E75",

  // "The model said so" accent — used sparingly
  ai: "#8B6FFF",

  // Data visualization
  chartPrimary: "#2FE0FF",
  chartSecondary: "#8B6FFF",
  chartTertiary: "#4C8DFF",

  // Risk meaning (independent of brand accent, by design)
  high: "#FF4D6D",
  medium: "#FFB020",
  low: "#2EE6A8",

  red: "#FF4D6D",
  green: "#2EE6A8",
};
