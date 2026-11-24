import { useAlerts } from '../../context/AlertContext.jsx';
import { useTranslation } from '../../i18n/useTranslation.js';
import Card from '../../components/Card.jsx';
import Button from '../../components/Button.jsx';
import RiskBadge from '../../components/RiskBadge.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import Alert from '../../components/Alert.jsx';

function relativeTime(value, t) {
  const hours = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 3600000));
  if (hours < 1) return t('common.minutesAgo', { n: Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 60000)) });
  if (hours < 24) return t('common.hoursAgo', { n: hours });
  return t('common.daysAgo', { n: Math.floor(hours / 24) });
}

export default function GrowerAlerts() {
  const { alerts, unreadCount, loadError, markRead, markAllRead } = useAlerts();
  const { t } = useTranslation();
  const sorted = [...alerts].sort((a, b) => Number(a.read) - Number(b.read) || new Date(b.time) - new Date(a.time));
  return <div className="fg-grid" style={{ gap: 18 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}><div><h1>{t('grower.alerts.title')}</h1><p className="text-muted">{t('grower.alerts.subtitle')}</p></div>{unreadCount > 0 && <Button variant="secondary" onClick={markAllRead}>{t('grower.alerts.markAllRead')}</Button>}</div>
    {loadError && <Alert variant="error" message={t('errors.loadFailed')} />}
    {sorted.length ? sorted.map((alert) => <Card key={alert.id} className={!alert.read ? 'pulse-soft' : ''} style={{ borderLeft: !alert.read ? '4px solid var(--color-accent)' : undefined }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}><RiskBadge level={alert.riskLevel} /><time className="text-muted" dateTime={alert.time}>{relativeTime(alert.time, t)}</time></div>
      <h2>{alert.title}</h2><p>{alert.message}</p><strong>{t('grower.alerts.whatToDo')}</strong><ul>{alert.whatToDo.map((step) => <li key={step}>{step}</li>)}</ul>
      {!alert.read && <Button size="sm" variant="ghost" onClick={() => markRead(alert.id)}>{t('grower.alerts.markRead')}</Button>}
    </Card>) : loadError ? null : <EmptyState title={t('grower.alerts.empty')} message={t('grower.alerts.emptyMessage')} />}
  </div>;
}
