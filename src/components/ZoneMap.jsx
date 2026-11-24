import { forwardRef, useEffect, useImperativeHandle } from 'react';
import { CircleMarker, MapContainer, Polygon, Popup, TileLayer, useMap } from 'react-leaflet';
import { MAP_CENTER, MAP_ZOOM_DEFAULT, PROBLEM_TRANSLATION_KEYS } from '../config.js';
import RiskBadge from './RiskBadge.jsx';
import { useTranslation } from '../i18n/useTranslation.js';
import 'leaflet/dist/leaflet.css';

const riskColors = { Low: 'var(--risk-low)', Medium: 'var(--risk-medium)', High: 'var(--risk-high)' };

function MapController({ controllerRef, zones }) {
  const map = useMap();
  useEffect(() => {
    const points = zones.flatMap((zone) => zone.coords?.length
      ? zone.coords
      : zone.latitude != null && zone.longitude != null
        ? [[zone.latitude, zone.longitude]]
        : []);
    if (points.length > 1) map.fitBounds(points, { padding: [24, 24], maxZoom: MAP_ZOOM_DEFAULT });
    else if (points.length === 1) map.setView(points[0], MAP_ZOOM_DEFAULT);
  }, [map, zones]);
  useImperativeHandle(controllerRef, () => ({
    flyToZone(zone) {
      const points = zone.coords || [];
      if (points.length < 3) {
        const point = points[0] || (zone.latitude != null && zone.longitude != null
          ? [zone.latitude, zone.longitude]
          : null);
        if (point) map.flyTo(point, 11, { duration: 0.7 });
        return;
      }
      const center = points.slice(0, -1).reduce((sum, point) => [sum[0] + point[0], sum[1] + point[1]], [0, 0]).map((n) => n / Math.max(1, points.length - 1));
      map.flyTo(center, 11, { duration: 0.7 });
    },
  }), [map]);
  return null;
}

const ZoneMap = forwardRef(function ZoneMap({ zones = [], ariaLabel, popupPrefix = 'grower.map' }, ref) {
  const { t } = useTranslation();
  return <div className="fg-map-frame" role="region" aria-label={ariaLabel}>
    <MapContainer center={MAP_CENTER} zoom={MAP_ZOOM_DEFAULT} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
      <MapController controllerRef={ref} zones={zones} />
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {zones.map((zone) => {
        const popup = <Popup>
          <div style={{ display: 'grid', gap: 8, minWidth: 180 }}>
            <strong>{zone.name}</strong><RiskBadge level={zone.riskLevel} />
            <span>{zone.reportCount} {t('grower.map.popupReports')}</span>
            <div><strong>{t('grower.map.popupMainProblems')}:</strong> {(zone.mainProblems || []).map((problem) => t(PROBLEM_TRANSLATION_KEYS[problem] || 'common.unknown')).join(', ') || t('common.unknown')}</div>
            {zone.weather && <small>{t('grower.map.popupWeather')} · {t('grower.map.popupTemp', { temp: zone.weather.temp })} · {t('grower.map.popupHumidity', { humidity: zone.weather.humidity })}</small>}
          </div>
        </Popup>;
        const color = riskColors[zone.riskLevel] || riskColors.Low;
        if (zone.coords?.length >= 3) {
          return <Polygon
            key={zone.id}
            positions={zone.coords}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.24, weight: 2 }}
            aria-label={t(`${popupPrefix}.ariaZonePolygon`, { name: zone.name, riskLevel: t(`common.severityLevel.${zone.riskLevel.toLowerCase()}`) })}
          >{popup}</Polygon>;
        }
        if (zone.latitude != null && zone.longitude != null) {
          return <CircleMarker
            key={zone.id}
            center={[zone.latitude, zone.longitude]}
            radius={12}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.72, weight: 2 }}
            aria-label={t(`${popupPrefix}.ariaZonePolygon`, { name: zone.name, riskLevel: t(`common.severityLevel.${zone.riskLevel.toLowerCase()}`) })}
          >{popup}</CircleMarker>;
        }
        return null;
      })}
    </MapContainer>
  </div>;
});

export default ZoneMap;
