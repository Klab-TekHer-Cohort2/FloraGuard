import { useEffect, useMemo, useState } from 'react';
import { Bell, CheckCircle, MapPin, FileText } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { PROBLEM_TRANSLATION_KEYS } from '../../config.js';
import { getAreaRisk, getReports } from '../../api.js';
import { useAlerts } from '../../context/AlertContext.jsx';
import { useTranslation } from '../../i18n/useTranslation.js';
import Card from '../../components/Card.jsx';
import Badge from '../../components/Badge.jsx';
import RiskBadge from '../../components/RiskBadge.jsx';
import SeverityMeter from '../../components/SeverityMeter.jsx';
import Skeleton from '../../components/Skeleton.jsx';
import Alert from '../../components/Alert.jsx';
import Button from '../../components/Button.jsx';

const palette = ['var(--color-primary)', 'var(--color-accent)', 'var(--risk-medium)', '#598C70', '#9E5B79', '#88A99A', '#C48B4B'];

export default function Overview() {
  const { t } = useTranslation();
  const { unreadCount } = useAlerts();
  const [reports, setReports] = useState(null);
  const [zones, setZones] = useState(null);
  const [reportsError, setReportsError] = useState(false);
  const [riskError, setRiskError] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    getReports().then((items) => { if (active) { setReports(items); setReportsError(false); } }).catch((error) => {
      console.error('[Overview] Could not load reports', error);
      if (active) setReportsError(true);
    });
    getAreaRisk().then((items) => { if (active) { setZones(items); setRiskError(false); } }).catch((error) => {
      console.error('[Overview] Could not load area risk', error);
      if (active) setRiskError(true);
    });
    return () => { active = false; };
  }, [loadAttempt]);
  const loadError = reportsError || riskError;
  const data = useMemo(() => reports || [], [reports]);
  const sevenDaysAgo = Date.now() - 7 * 86400000;
  const highRiskZones = zones?.filter((zone) => zone.riskLevel === 'High').length;
  const kpis = [
    [FileText, data.filter((report) => new Date(report.date).getTime() >= sevenDaysAgo).length, 'dashboard.overview.totalReports', reports === null],
    [CheckCircle, data.filter((report) => report.status === 'confirmed').length, 'dashboard.overview.confirmedCases', reports === null],
    [MapPin, highRiskZones ?? 0, 'dashboard.overview.highRiskZones', zones === null],
    [Bell, unreadCount, 'dashboard.overview.unreadAlerts', false],
  ];
  const dailyData = useMemo(() => Array.from({ length: 14 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() - (13 - index));
    const key = date.toISOString().slice(0, 10);
    const dayReports = data.filter((report) => report.date.slice(0, 10) === key);
    return { day: date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), Low: dayReports.filter((r) => r.severity === 'Low').length, Medium: dayReports.filter((r) => r.severity === 'Medium').length, High: dayReports.filter((r) => r.severity === 'High').length, Unknown: dayReports.filter((r) => r.severity === 'Unknown').length };
  }), [data]);
  const problems = Object.entries(data.reduce((counts, report) => { counts[report.problem] = (counts[report.problem] || 0) + 1; return counts; }, {})).map(([problem, value]) => ({ name: t(PROBLEM_TRANSLATION_KEYS[problem] || 'common.unknown'), value }));
  const recent = [...data].filter((r) => r.status !== 'dismissed' && ['Medium', 'High'].includes(r.riskLevel)).sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 5);
  return <main className="fg-page fg-dashboard-content">
    <h1>{t('dashboard.overview.title')}</h1><p className="text-muted">{t('dashboard.overview.subtitle')}</p>
    {loadError && <Alert variant="error" title={t('errors.loadFailed')}><Button size="sm" onClick={() => { setReportsError(false); setRiskError(false); setLoadAttempt((attempt) => attempt + 1); }}>{t('common.retry')}</Button></Alert>}
    <div className="fg-grid fg-four-col" style={{ margin: '22px 0' }}>{kpis.map(([Icon, value, key, loading]) => <Card key={key}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}><span className="text-muted">{t(key)}</span><Icon color="var(--color-primary)" size={20} /></div><strong style={{ display: 'block', margin: '10px 0', fontSize: 30 }}>{loading && !loadError ? <Skeleton style={{ width: 60 }} /> : value}</strong><Badge label={t('dashboard.overview.subtitle')} color="var(--color-primary)" bgColor="var(--color-primary-tint)" /></Card>)}</div>
    <div className="fg-grid fg-two-col">
      <Card><h2>{t('dashboard.overview.reportsByDay')}</h2><p className="text-muted">{t('dashboard.overview.reportsByDaySubtitle')}</p><div className="fg-chart"><ResponsiveContainer><BarChart data={dailyData}><CartesianGrid stroke="var(--color-border)" vertical={false} /><XAxis dataKey="day" /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="Low" fill="var(--risk-low)" /><Bar dataKey="Medium" fill="var(--risk-medium)" /><Bar dataKey="High" fill="var(--risk-high)" /><Bar dataKey="Unknown" fill="var(--color-text-muted)" /></BarChart></ResponsiveContainer></div></Card>
      <Card><h2>{t('dashboard.overview.problemBreakdown')}</h2><div className="fg-chart"><ResponsiveContainer><PieChart><Pie data={problems} dataKey="value" nameKey="name" outerRadius="75%" label>{problems.map((entry, index) => <Cell key={entry.name} fill={palette[index % palette.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div></Card>
    </div>
    <section style={{ marginTop: 24 }}><h2>{t('dashboard.overview.recentHighRisk')}</h2><div className="fg-grid">{recent.map((report) => <Card key={report.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}><Badge label={`${t('common.zone')} ${report.zone}`} /><Badge label={t(PROBLEM_TRANSLATION_KEYS[report.problem] || 'common.unknown')} /></div>{report.severity !== 'Unknown' && <SeverityMeter value={report.severity === 'High' ? 85 : report.severity === 'Medium' ? 55 : 25} compact />}<span>{report.confidence == null ? t('common.unknown') : `${report.confidence}%`}</span><time dateTime={report.date}>{new Date(report.date).toLocaleDateString()}</time><RiskBadge level={report.riskLevel} />
    </Card>)}</div></section>
  </main>;
}
