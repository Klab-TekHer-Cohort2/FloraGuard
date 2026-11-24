import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowRight, Bell, Leaf, MapPin } from 'lucide-react';
import { getAreaRisk } from '../../api.js';
import { AREA_NAME } from '../../config.js';
import { useAlerts } from '../../context/AlertContext.jsx';
import { useTranslation } from '../../i18n/useTranslation.js';
import Card from '../../components/Card.jsx';
import Button from '../../components/Button.jsx';
import RiskBadge from '../../components/RiskBadge.jsx';
import Skeleton from '../../components/Skeleton.jsx';
import Alert from '../../components/Alert.jsx';

const riskRank = { Low: 0, Medium: 1, High: 2 };

export default function GrowerHome() {
  const { t } = useTranslation();
  const { alerts } = useAlerts();
  const [zones, setZones] = useState(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const loadZones = useCallback(() => {
    let active = true;
    setError(false);
    getAreaRisk()
      .then((data) => { if (active) setZones(data); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, []);

  useEffect(() => loadZones(), [loadZones, attempt]);

  const highest = zones?.length
    ? zones.reduce((top, zone) => (riskRank[zone.riskLevel] > riskRank[top.riskLevel] ? zone : top))
    : null;
  const highRiskZones = zones?.filter((zone) => zone.riskLevel === 'High').length ?? 0;
  const activeAlerts = alerts.filter((alert) => new Date(alert.time).getTime() > Date.now() - 24 * 60 * 60 * 1000);
  const recent = [...alerts]
    .sort((a, b) => Number(a.read) - Number(b.read) || new Date(b.time) - new Date(a.time))
    .slice(0, 3);

  return (
    <div className="fg-home">
      <header className="fg-home-heading">
        <p className="fg-eyebrow"><MapPin size={16} />{AREA_NAME}</p>
        <h1>{t('grower.home.greeting')}!</h1>
        <p>{t('grower.home.dashboardSubtitle')}</p>
      </header>

      <section className="fg-home-overview" aria-label={t('grower.home.areaRisk')}>
        <div className="fg-home-overview-main">
          <div className="fg-home-overview-copy">
            <span className="fg-home-overview-label"><Activity size={15} />{t('grower.home.areaRisk')}</span>
            <h2>{t('grower.home.title')}</h2>
            <p>{t(!zones ? 'grower.home.areaRiskLoading' : highest?.riskLevel === 'High' ? 'grower.home.riskNeedsAttention' : highest?.riskLevel === 'Medium' ? 'grower.home.riskModerate' : 'grower.home.riskLooksCalm')}</p>
          </div>
          <div className="fg-home-overview-badge">
            {!zones && !error
              ? <Skeleton style={{ width: 110, height: 34 }} />
              : error
                ? <span className="fg-home-risk-error" role="status">{t('errors.loadFailed')}</span>
                : <RiskBadge level={highest?.riskLevel || 'Low'} />}
          </div>
        </div>
        <div className="fg-home-stats">
          <div><strong>{zones?.length ?? '—'}</strong><span>{t('grower.home.zonesMonitored')}</span></div>
          <div><strong>{activeAlerts.length}</strong><span>{t('grower.home.activeWarnings')}</span></div>
          <div><strong>{highRiskZones}</strong><span>{t('grower.home.highRiskZones')}</span></div>
        </div>
        <div className="fg-home-overview-footer">
          <span>{highest?.name ? `${t('grower.home.highestRiskZone')}: ${highest.name}` : t('grower.home.monitoringNote')}</span>
          <Link to="/grower/map">{t('grower.home.viewMap')} <ArrowRight size={15} /></Link>
        </div>
      </section>

      {error && (
        <Alert variant="error" title={t('errors.loadFailed')}>
          <Button size="sm" onClick={() => setAttempt((value) => value + 1)}>{t('common.retry')}</Button>
        </Alert>
      )}

      <Link to="/grower/check" className="fg-home-check-link">
        <div className="fg-home-check">
          <span className="fg-home-check-icon"><Leaf size={22} /></span>
          <span className="fg-home-check-copy">
            <strong>{t('grower.home.checkButton')}</strong>
            <small>{t('grower.home.checkSubtitle')}</small>
          </span>
          <span className="fg-home-check-arrow"><ArrowRight size={19} /></span>
        </div>
      </Link>

      <section className="fg-home-alert-section">
        <div className="fg-home-section-heading">
          <div>
            <span className="fg-home-section-kicker"><Bell size={14} />{t('grower.home.communityUpdates')}</span>
            <h2>{t('grower.home.recentAlerts')}</h2>
          </div>
          <Link to="/grower/alerts">{t('grower.home.viewAllAlerts')} <ArrowRight size={15} /></Link>
        </div>
        {recent.length ? (
          <div className="fg-home-alert-list">
            {recent.map((alert) => (
              <Link key={alert.id} to="/grower/alerts" className="fg-home-alert-link">
                <Card className="fg-home-alert-card">
                  <span className={`fg-home-alert-dot ${alert.riskLevel.toLowerCase()}`} />
                  <span className="fg-home-alert-copy">
                    <strong>{alert.title}</strong>
                    <small>{t('common.zone')} {alert.zone} <span aria-hidden="true">·</span> {new Date(alert.time).toLocaleDateString()}</small>
                  </span>
                  <RiskBadge level={alert.riskLevel} />
                  <ArrowRight className="fg-home-alert-arrow" size={17} />
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card className="fg-home-empty-alert">
            <Bell size={20} />
            <span><strong>{t('grower.home.noAlerts')}</strong><small>{t('grower.home.noAlertsMessage')}</small></span>
          </Card>
        )}
      </section>
    </div>
  );
}
