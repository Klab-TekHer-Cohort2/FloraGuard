import { useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAlerts } from '../../context/AlertContext.jsx';
import { useTranslation } from '../../i18n/useTranslation.js';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import RiskBadge from '../../components/RiskBadge.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import Alert from '../../components/Alert.jsx';

function relativeTime(value, t) {
  const hours = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 3600000));
  if (hours < 1) return t('common.minutesAgo', { n: Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 60000)) });
  if (hours < 24) return t('common.hoursAgo', { n: hours });
  return t('common.daysAgo', { n: Math.floor(hours / 24) });
}

export default function DashboardAlerts() {
  const { alerts, loadError, markRead } = useAlerts();
  const { t } = useTranslation();
  const [risk, setRisk] = useState('');
  const [read, setRead] = useState('');
  const filtered = alerts.filter((alert) => (!risk || alert.riskLevel === risk) && (!read || (read === 'Unread' ? !alert.read : alert.read)));
  const timeline = useMemo(() => Array.from({ length: 14 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() - (13 - index));
    const day = date.toISOString().slice(0, 10);
    return { day: date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), count: alerts.filter((alert) => alert.time.slice(0, 10) === day).length };
  }), [alerts]);
  return <main className="fg-page fg-dashboard-content">
    <h1>{t('dashboard.alerts.title')}</h1><p className="text-muted">{t('dashboard.alerts.subtitle')}</p>
    {loadError && <Alert variant="error" message={t('errors.loadFailed')} />}
    <Card style={{ margin: '18px 0' }}><h2>{t('dashboard.alerts.timeline')}</h2><p className="text-muted">{t('dashboard.alerts.timelineSubtitle')}</p><div className="fg-chart"><ResponsiveContainer><LineChart data={timeline}><CartesianGrid stroke="var(--color-border)" vertical={false} /><XAxis dataKey="day" /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="count" name={t('dashboard.alerts.title')} stroke="var(--color-primary)" strokeWidth={3} dot /></LineChart></ResponsiveContainer></div></Card>
    <div className="fg-filter-row" style={{ marginBottom: 16 }}>
      <label>{t('dashboard.alerts.filterRisk')} <select value={risk} onChange={(e) => setRisk(e.target.value)}><option value="">{t('dashboard.alerts.filterAll')}</option>{['Low', 'Medium', 'High'].map((level) => <option key={level} value={level}>{t(`common.severityLevel.${level.toLowerCase()}`)}</option>)}</select></label>
      <label>{t('dashboard.alerts.filterRead')} <select value={read} onChange={(e) => setRead(e.target.value)}><option value="">{t('dashboard.alerts.filterAll')}</option><option value="Unread">{t('dashboard.alerts.filterUnread')}</option><option value="Read">{t('dashboard.alerts.filterRead2')}</option></select></label>
      {filtered.some((alert) => !alert.read) && <Button variant="secondary" onClick={() => filtered.filter((alert) => !alert.read).forEach((alert) => markRead(alert.id))}>{t('dashboard.alerts.bulkMarkRead')}</Button>}
    </div>
    {filtered.length ? <div className="fg-grid">{filtered.map((alert) => <Card key={alert.id} style={{ borderLeft: alert.read ? undefined : '4px solid var(--color-accent)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}><RiskBadge level={alert.riskLevel} /><time dateTime={alert.time} className="text-muted">{relativeTime(alert.time, t)}</time></div>
      <h2>{alert.title}</h2><p>{alert.message}</p><strong>{t('grower.alerts.whatToDo')}</strong><ul>{alert.whatToDo.map((item) => <li key={item}>{item}</li>)}</ul>
      {!alert.read && <Button size="sm" variant="ghost" onClick={() => markRead(alert.id)}>{t('common.markRead')}</Button>}
    </Card>)}</div> : loadError ? null : <EmptyState title={t('dashboard.alerts.empty')} message={t('dashboard.alerts.emptyMessage')} />}
  </main>;
}
