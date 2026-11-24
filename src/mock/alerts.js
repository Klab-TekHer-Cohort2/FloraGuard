/**
 * MOCK_ALERTS — 6 community alert objects.
 *
 * Messages are under 15 words. Zone labels never use farm names.
 */

function hoursAgo(h) {
  const d = new Date();
  d.setHours(d.getHours() - h);
  return d.toISOString();
}

export const MOCK_ALERTS = [
  {
    id: 'alt-001',
    riskLevel: 'High',
    title: 'Spider mite outbreak — Zone B',
    message: 'Multiple farms report spider mites. Act quickly to protect your roses.',
    whatToDo: [
      'Inspect leaves for fine webbing and tiny dots.',
      'Apply a recommended miticide if confirmed.',
      'Isolate affected plants where possible.',
    ],
    time: hoursAgo(3),
    read: false,
    zone: 'B',
  },
  {
    id: 'alt-002',
    riskLevel: 'High',
    title: 'Grey mould spreading — Zone B',
    message: 'Botrytis confirmed in Zone B. Remove infected blooms immediately.',
    whatToDo: [
      'Remove and destroy all grey-mouldy flowers.',
      'Improve airflow between plants.',
      'Avoid overhead watering during evenings.',
    ],
    time: hoursAgo(8),
    read: false,
    zone: 'B',
  },
  {
    id: 'alt-003',
    riskLevel: 'Medium',
    title: 'Powdery mildew rising — Zone A',
    message: 'Powdery mildew cases increasing. Humidity is high this week.',
    whatToDo: [
      'Check leaves for white powdery patches.',
      'Apply a sulphur-based fungicide if needed.',
      'Prune to improve air circulation.',
    ],
    time: hoursAgo(18),
    read: false,
    zone: 'A',
  },
  {
    id: 'alt-004',
    riskLevel: 'Medium',
    title: 'Downy mildew detected — Zone C',
    message: 'Early downy mildew found in Zone C. Watch your leaves closely.',
    whatToDo: [
      'Look for pale yellow patches on upper leaves.',
      'Remove affected leaves and dispose away from plants.',
      'Consider a copper-based fungicide spray.',
    ],
    time: hoursAgo(30),
    read: true,
    zone: 'C',
  },
  {
    id: 'alt-005',
    riskLevel: 'Low',
    title: 'Thrips activity — Zone D',
    message: 'Low-level thrips activity spotted. Monitor your buds and petals.',
    whatToDo: [
      'Check buds and flower edges for tiny insects.',
      'Use sticky traps to monitor population levels.',
      'Consult your agronomist if activity increases.',
    ],
    time: hoursAgo(48),
    read: true,
    zone: 'D',
  },
  {
    id: 'alt-006',
    riskLevel: 'Low',
    title: 'Black spot risk — Zone E',
    message: 'Black spot risk is low after recent rain. Keep leaves dry.',
    whatToDo: [
      'Avoid wetting foliage when watering.',
      'Remove fallen leaves from around plants.',
      'Monitor for circular dark spots on leaves.',
    ],
    time: hoursAgo(60),
    read: true,
    zone: 'E',
  },
];
