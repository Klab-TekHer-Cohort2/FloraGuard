/**
 * MOCK_ZONES — 5 geographic zone objects for the community map.
 *
 * Polygon coordinates are rough areas near Rwanda's rose-growing belt.
 * Zones never use specific farm or town names.
 * Risk distribution: 1 High, 2 Medium, 2 Low.
 */

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

export const MOCK_ZONES = [
  {
    id: 'zone-a',
    name: 'Zone A',
    riskLevel: 'Medium',
    // Rough polygon north of Rwanda centre
    coords: [
      [-1.49, 29.72],
      [-1.49, 29.78],
      [-1.56, 29.78],
      [-1.56, 29.72],
      [-1.49, 29.72],
    ],
    reportCount: 8,
    mainProblems: ['Powdery mildew', 'Spider mite'],
    lastUpdate: daysAgo(1),
    weather: { temp: 19, humidity: 72 },
  },
  {
    id: 'zone-b',
    name: 'Zone B',
    riskLevel: 'High',
    // Rough polygon east cluster
    coords: [
      [-1.75, 29.99],
      [-1.75, 30.06],
      [-1.82, 30.06],
      [-1.82, 29.99],
      [-1.75, 29.99],
    ],
    reportCount: 8,
    mainProblems: ['Spider mite', 'Grey mould (Botrytis)'],
    lastUpdate: daysAgo(0),
    weather: { temp: 21, humidity: 68 },
  },
  {
    id: 'zone-c',
    name: 'Zone C',
    riskLevel: 'Medium',
    // Rough polygon central
    coords: [
      [-1.93, 29.86],
      [-1.93, 29.91],
      [-1.98, 29.91],
      [-1.98, 29.86],
      [-1.93, 29.86],
    ],
    reportCount: 8,
    mainProblems: ['Downy mildew', 'Black spot'],
    lastUpdate: daysAgo(1),
    weather: { temp: 20, humidity: 75 },
  },
  {
    id: 'zone-d',
    name: 'Zone D',
    riskLevel: 'Low',
    // Rough polygon south cluster
    coords: [
      [-2.27, 29.68],
      [-2.27, 29.74],
      [-2.34, 29.74],
      [-2.34, 29.68],
      [-2.27, 29.68],
    ],
    reportCount: 8,
    mainProblems: ['Grey mould (Botrytis)', 'Thrips'],
    lastUpdate: daysAgo(2),
    weather: { temp: 18, humidity: 80 },
  },
  {
    id: 'zone-e',
    name: 'Zone E',
    riskLevel: 'Low',
    // Rough polygon west cluster
    coords: [
      [-2.03, 29.33],
      [-2.03, 29.39],
      [-2.09, 29.39],
      [-2.09, 29.33],
      [-2.03, 29.33],
    ],
    reportCount: 8,
    mainProblems: ['Black spot', 'Spider mite'],
    lastUpdate: daysAgo(3),
    weather: { temp: 17, humidity: 83 },
  },
];
