import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { AREA_NAME } from '../../config.js';
import { getAreaRisk } from '../../api.js';
import { useTranslation } from '../../i18n/useTranslation.js';
import { ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import RiskBadge from '../../components/RiskBadge.jsx';
import Card from '../../components/Card.jsx';
import Skeleton from '../../components/Skeleton.jsx';
import Alert from '../../components/Alert.jsx';

const ZoneMap = lazy(() => import('../../components/ZoneMap.jsx'));
const riskRank = { All: true, Low: true, Medium: true, High: true };
const legend = [['Low', ShieldCheck], ['Medium', ShieldAlert], ['High', ShieldX]];

export default function MapView() {
  const { t } = useTranslation();
  const [zones, setZones] = useState(null);
  const [risk, setRisk] = useState('All');
  const [error, setError] = useState(false);
  const mapRef = useRef(null);
  useEffect(() => {
    let active = true;
    getAreaRisk().then((items) => { if (active) setZones(items); }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, []);
  const visibleZones = (zones || []).filter((zone) => risk === 'All' || zone.riskLevel === risk);
  return <div className="fg-page fg-dashboard-content">
    <p className="text-muted">{AREA_NAME}</p><h1>{t('dashboard.map.title')}</h1><p className="text-muted">{t('dashboard.map.subtitle')}</p>
    <div className="fg-filter-row" style={{ margin: '16px 0' }}><label htmlFor="map-risk-filter">{t('dashboard.map.filterLabel')}</label><select id="map-risk-filter" value={risk} onChange={(event) => setRisk(event.target.value)}>{Object.keys(riskRank).map((level) => <option key={level} value={level}>{t(level === 'All' ? 'dashboard.map.filterAll' : `dashboard.map.filter${level}`)}</option>)}</select></div>
    {error && <Alert variant="error" message={t('errors.loadFailed')} />}
    {!zones && !error ? <Skeleton variant="block" style={{ height: 480 }} /> : zones && <div className="fg-map-layout">
      <aside className="fg-zone-list" aria-label={t('dashboard.map.zonePanelAriaLabel')} style={{ display: 'grid', alignContent: 'start', gap: 8 }}>
        <h2 style={{ margin: '0 0 4px' }}>{t('dashboard.map.zonesPanel')}</h2>
        {zones.map((zone) => <Card key={zone.id} padding={12} onClick={() => mapRef.current?.flyToZone(zone)} aria-label={t('dashboard.map.flyToZone')} style={{ cursor: 'pointer' }}><strong>{zone.name}</strong><div style={{ marginTop: 8 }}><RiskBadge level={zone.riskLevel} /></div><small>{zone.reportCount} {t('grower.map.popupReports')}</small></Card>)}
      </aside>
      <div>
        <Suspense fallback={<Skeleton variant="block" style={{ height: 500 }} />}><ZoneMap ref={mapRef} zones={visibleZones} ariaLabel={t('dashboard.map.ariaMapContainer')} popupPrefix="dashboard.map" /></Suspense>
        <section aria-label={t('dashboard.map.legend')} style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginTop: 12 }}>
          <strong>{t('dashboard.map.legend')}:</strong>{legend.map(([level, Icon]) => <span key={level} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: level === 'Medium' ? 'var(--risk-medium-text)' : `var(--risk-${level.toLowerCase()})` }}><Icon size={17} />{t(`dashboard.map.legend${level}`)}</span>)}
        </section>
      </div>
    </div>}
  </div>;
}
