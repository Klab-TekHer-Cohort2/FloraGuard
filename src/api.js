/**
 * FloraGuard API client.
 *
 * Set VITE_API_BASE_URL to the backend's /api URL when deploying.
 */

const API_BASE_URL = new URL(
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  window.location.origin
).href.replace(/\/+$/, '');
const QUEUED_REPORTS_KEY = 'fg_queued_reports';
let queuedReportSyncPromise = null;
const PROBLEM_LABELS = {
  healthy: 'Healthy',
  spider_mite: 'Spider mite',
  thrips: 'Thrips',
  powdery_mildew: 'Powdery mildew',
  downy_mildew: 'Downy mildew',
  grey_mould: 'Grey mould (Botrytis)',
  black_spot: 'Black spot',
  uncertain: 'Unknown',
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 60000);
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...options.headers },
    });
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new ApiError('The FloraGuard backend took too long to respond. Please try again.');
    }
    throw new ApiError('Could not reach the FloraGuard backend. Check that it is running and try again.');
  } finally {
    window.clearTimeout(timeout);
  }

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      throw new ApiError('The FloraGuard backend returned an invalid response.', response.status);
    }
  }

  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(' ')
      : detail || `FloraGuard request failed (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  if (payload === null) {
    throw new ApiError('The FloraGuard backend returned an empty response.', response.status);
  }
  return payload;
}

function normalizeProblem(value) {
  return PROBLEM_LABELS[String(value || 'uncertain').toLowerCase()] || 'Unknown';
}

function normalizeLevel(value) {
  const level = String(value || 'unknown').toLowerCase();
  return ['low', 'medium', 'high'].includes(level)
    ? `${level[0].toUpperCase()}${level.slice(1)}`
    : 'Unknown';
}

function normalizeReport(report) {
  if (!report || typeof report !== 'object') {
    throw new ApiError('The FloraGuard backend returned an invalid report.');
  }
  const problem = report.reported_problem || report.predicted_problem || report.problem;
  const confidence = report.confidence == null ? null : Number(report.confidence);
  if (confidence !== null && (!Number.isFinite(confidence) || confidence < 0 || confidence > 1)) {
    throw new ApiError('The FloraGuard backend returned an invalid confidence score.');
  }
  const imageUrl = report.image_url ? new URL(report.image_url, API_BASE_URL).href : null;

  return {
    ...report,
    id: report.id,
    reportId: report.id,
    zone: report.area,
    problem: normalizeProblem(problem),
    severity: normalizeLevel(report.severity),
    confidence: confidence === null ? null : Math.round(confidence * 100),
    riskLevel: normalizeLevel(report.risk_level),
    riskScore: report.risk_score,
    riskReasons: report.risk_reasons || [],
    status: String(report.status || 'pending').toLowerCase(),
    date: report.timestamp,
    photo: imageUrl,
    imageUrl,
    lat: report.latitude,
    lng: report.longitude,
    aiStatus: report.ai_status,
    isSample: Boolean(report.is_sample),
    advice: [],
  };
}

/**
 * Upload and analyze a rose photo. The backend stores the report as part of this request.
 *
 * @param {Blob|File} photo - A compressed rose photo.
 * @returns {Promise<object>} The normalized report and diagnosis.
 */
export async function submitReport(photo) {
  if (!(photo instanceof Blob)) {
    throw new TypeError('submitReport expects a photo Blob or File.');
  }
  const form = new FormData();
  form.append('image', photo, 'rose-photo.jpg');
  return normalizeReport(await request('/reports', { method: 'POST', body: form }));
}

/** Save a photo locally until the browser reconnects. */
export async function queueReportOffline(photo) {
  if (!(photo instanceof Blob)) {
    throw new TypeError('queueReportOffline expects a photo Blob or File.');
  }
  const photoData = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Could not save photo offline.'));
    reader.readAsDataURL(photo);
  });
  const queue = readQueuedReports();
  queue.push({ photo: photoData, timestamp: new Date().toISOString() });
  localStorage.setItem(QUEUED_REPORTS_KEY, JSON.stringify(queue));
}

/** Upload locally queued reports after network connectivity returns. */
export async function syncQueuedReports() {
  if (typeof navigator === 'undefined' || !navigator.onLine) return 0;
  if (queuedReportSyncPromise) return queuedReportSyncPromise;
  queuedReportSyncPromise = uploadQueuedReports();
  try {
    return await queuedReportSyncPromise;
  } finally {
    queuedReportSyncPromise = null;
  }
}

async function uploadQueuedReports() {
  const queue = readQueuedReports();
  let synced = 0;

  while (queue.length && navigator.onLine) {
    const item = queue[0];
    if (typeof item?.photo !== 'string' || !item.photo.startsWith('data:image/')) {
      throw new ApiError('A saved offline report is invalid and could not be uploaded.');
    }
    const photoResponse = await fetch(item.photo);
    if (!photoResponse.ok) {
      throw new ApiError('A saved offline photo could not be read.');
    }
    await submitReport(await photoResponse.blob());
    queue.shift();
    localStorage.setItem(QUEUED_REPORTS_KEY, JSON.stringify(queue));
    synced += 1;
  }
  return synced;
}

function readQueuedReports() {
  const raw = localStorage.getItem(QUEUED_REPORTS_KEY);
  if (!raw) return [];
  let queue;
  try {
    queue = JSON.parse(raw);
  } catch {
    throw new ApiError('Saved offline reports could not be read.');
  }
  if (!Array.isArray(queue)) {
    throw new ApiError('Saved offline reports are in an invalid format.');
  }
  return queue;
}

/** Fetch persisted inspection reports. */
export async function getReports() {
  const reports = await request('/reports');
  if (!Array.isArray(reports)) {
    throw new ApiError('The FloraGuard backend returned an invalid reports list.');
  }
  return reports.map(normalizeReport);
}

/** Fetch privacy-preserving area aggregates for the map. */
export async function getAreaRisk() {
  const response = await request('/map/reports');
  if (!Array.isArray(response.areas)) {
    throw new ApiError('The FloraGuard backend returned invalid map data.');
  }
  return response.areas.map((area) => ({
    id: area.area,
    name: area.area,
    riskLevel: normalizeLevel(area.risk_level),
    riskScore: area.risk_score,
    reportCount: area.report_count,
    mainProblems: area.problem ? [normalizeProblem(area.problem)] : [],
    latitude: area.latitude,
    longitude: area.longitude,
    coords: area.latitude == null || area.longitude == null
      ? []
      : [[area.latitude, area.longitude]],
    weather: null,
    isSample: Boolean(area.is_sample),
  }));
}

/** Fetch and adapt alerts to the shape consumed by FloraGuard screens. */
export async function getAlerts() {
  const alerts = await request('/alerts');
  if (!Array.isArray(alerts)) {
    throw new ApiError('The FloraGuard backend returned an invalid alerts list.');
  }
  return alerts.map((alert) => ({
    id: alert.id,
    riskLevel: normalizeLevel(alert.risk_level),
    title: `${normalizeProblem(alert.problem)} — ${alert.area}`,
    message: alert.guidance,
    whatToDo: alert.guidance ? [alert.guidance] : [],
    time: alert.created_at,
    read: false,
    zone: alert.area,
    reportId: alert.report_id,
  }));
}
