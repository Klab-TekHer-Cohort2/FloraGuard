/**
 * FloraGuard — Runtime Configuration
 *
 * Update AREA_NAME and MAP_CENTER before deployment to match
 * the target rose-growing region. Do not name specific farms.
 */

/** Update to the real area name before deployment */
export const AREA_NAME = 'Gishari Flower Park';

/**
 * Approximate centre of Rwanda — update to the target rose-growing region
 * Format: [latitude, longitude]
 */
export const MAP_CENTER = [-1.9403, 29.8739];

/** Default zoom level for the community and dashboard maps */
export const MAP_ZOOM_DEFAULT = 9;

/** All possible AI-detected problem types */
export const PROBLEMS = [
  'Healthy',
  'Spider mite',
  'Thrips',
  'Powdery mildew',
  'Downy mildew',
  'Grey mould (Botrytis)',
  'Black spot',
];

/** Translation key for each problem label shown in the interface. */
export const PROBLEM_TRANSLATION_KEYS = {
  Healthy: 'common.problems.healthy',
  'Spider mite': 'common.problems.spiderMite',
  Thrips: 'common.problems.thrips',
  'Powdery mildew': 'common.problems.powderyMildew',
  'Downy mildew': 'common.problems.downyMildew',
  'Grey mould (Botrytis)': 'common.problems.greyMould',
  'Black spot': 'common.problems.blackSpot',
};

/** Severity levels reported by the AI */
export const SEVERITY_LEVELS = ['Low', 'Medium', 'High'];

/** Area risk levels */
export const RISK_LEVELS = ['Low', 'Medium', 'High'];

/** Confidence threshold below which the app shows the low-confidence state */
export const LOW_CONFIDENCE_THRESHOLD = 60;
