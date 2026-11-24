import { lazy, Suspense, useEffect, useState } from 'react';
import { ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { getAreaRisk } from '../../api.js';
import { AREA_NAME } from '../../config.js';
import { useTranslation } from '../../i18n/useTranslation.js';
import Skeleton from '../../components/Skeleton.jsx';
import Alert from '../../components/Alert.jsx';

const ZoneMap = lazy(() => import('../../components/ZoneMap.jsx'));
const legend = [['Low', ShieldCheck], ['Medium', ShieldAlert], ['High', ShieldX]];

export default function CommunityMap() {
  const { t } = useTranslation();
  const [zones, setZones] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    getAreaRisk().then((items) => { if (active) setZones(items); }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, []);
  return <div className="fg-grid" style={{ gap: 16 }}>
    <div><p className="text-muted">{AREA_NAME}</p><h1>{t('grower.map.title')}</h1><p className="text-muted">{t('grower.map.subtitle')}</p></div>
    {error && <Alert variant="error" message={t('errors.loadFailed')} />}
    {!zones && !error ? <Skeleton variant="block" style={{ height: 480 }} /> : zones && <>
      <Suspense fallback={<Skeleton variant="block" style={{ height: 480 }} />}><ZoneMap zones={zones} ariaLabel={t('grower.map.ariaMapContainer')} /></Suspense>
      <section aria-label={t('grower.map.legend')} style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        <strong>{t('grower.map.legend')}:</strong>{legend.map(([level, Icon]) => <span key={level} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: level === 'Medium' ? 'var(--risk-medium-text)' : `var(--risk-${level.toLowerCase()})` }}><Icon size={17} />{t(`grower.map.legend${level}`)}</span>)}
      </section>
    </>}
  </div>;
}
