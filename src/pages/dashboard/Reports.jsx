import { useEffect, useMemo, useState } from 'react';
import { getReports } from '../../api.js';
import { PROBLEMS, PROBLEM_TRANSLATION_KEYS } from '../../config.js';
import { useTranslation } from '../../i18n/useTranslation.js';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Badge from '../../components/Badge.jsx';
import RiskBadge from '../../components/RiskBadge.jsx';
import Modal from '../../components/Modal.jsx';
import EmptyState from '../../components/EmptyState.jsx';
import Skeleton from '../../components/Skeleton.jsx';
import Alert from '../../components/Alert.jsx';
import SeverityMeter from '../../components/SeverityMeter.jsx';

const PAGE_SIZE = 10;
const severityRank = { Unknown: 0, Low: 1, Medium: 2, High: 3 };

export default function Reports() {
  const { t } = useTranslation();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [search, setSearch] = useState('');
  const [problem, setProblem] = useState('');
  const [severity, setSeverity] = useState('');
  const [zone, setZone] = useState('');
  const [status, setStatus] = useState('');
  const [sort, setSort] = useState({ key: 'date', direction: 'desc' });
  const [page, setPage] = useState(1);
  const [pendingAction, setPendingAction] = useState(null);
  useEffect(() => {
    let active = true;
    getReports().then((data) => { if (active) setReports(data); }).catch((error) => {
      console.error('[Reports] Could not load reports', error);
      if (active) setLoadError(true);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [loadAttempt]);
  const filtered = useMemo(() => reports.filter((report) =>
    (!search || `${report.problem} ${report.zone}`.toLowerCase().includes(search.toLowerCase())) &&
    (!problem || report.problem === problem) && (!severity || report.severity === severity) &&
    (!zone || report.zone === zone) && (!status || report.status === status)
  ).sort((a, b) => {
    const left = sort.key === 'severity' ? severityRank[a.severity] : sort.key === 'confidence' ? a.confidence ?? -1 : sort.key === 'zone' ? a.zone : new Date(a.date).getTime();
    const right = sort.key === 'severity' ? severityRank[b.severity] : sort.key === 'confidence' ? b.confidence ?? -1 : sort.key === 'zone' ? b.zone : new Date(b.date).getTime();
    return (left > right ? 1 : left < right ? -1 : 0) * (sort.direction === 'asc' ? 1 : -1);
  }), [reports, search, problem, severity, zone, status, sort]);
  useEffect(() => setPage(1), [search, problem, severity, zone, status, sort]);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const zones = [...new Set(reports.map((report) => report.zone).filter(Boolean))].sort();
  const severities = [...new Set(reports.map((report) => report.severity))].sort((a, b) => severityRank[a] - severityRank[b]);
  const clear = () => { setSearch(''); setProblem(''); setSeverity(''); setZone(''); setStatus(''); };
  const headers = [['zone', 'common.zone'], ['problem', 'common.problem'], ['severity', 'common.severity'], ['confidence', 'common.confidence'], ['date', 'common.date']];
  const toggleSort = (key) => setSort((old) => ({ key, direction: old.key === key && old.direction === 'asc' ? 'desc' : 'asc' }));
  const act = () => {
    setReports((items) => items.map((item) => item.id === pendingAction.id ? { ...item, status: pendingAction.action === 'confirm' ? 'confirmed' : 'dismissed' } : item));
    setPendingAction(null);
  };
  const rows = pageItems.map((report) => <tr key={report.id}><td>{t('common.zone')} {report.zone}</td><td>{t(PROBLEM_TRANSLATION_KEYS[report.problem] || 'common.unknown')}</td><td><div style={{ display: 'grid', gap: 4 }}><RiskBadge level={report.severity} />{report.severity !== 'Unknown' && <SeverityMeter value={severityRank[report.severity] * 30 - 5} compact />}</div></td><td>{report.confidence == null ? t('common.unknown') : `${report.confidence}%`}</td><td>{new Date(report.date).toLocaleDateString()}</td><td><Badge label={t(`common.${report.status}`)} /></td><td style={{ display: 'flex', gap: 6 }}><Button size="sm" onClick={() => setPendingAction({ id: report.id, action: 'confirm' })}>{t('dashboard.reports.confirmAction')}</Button><Button size="sm" variant="ghost" onClick={() => setPendingAction({ id: report.id, action: 'dismiss' })}>{t('dashboard.reports.dismissAction')}</Button></td></tr>);
  return <main className="fg-page fg-dashboard-content">
    <h1>{t('dashboard.reports.title')}</h1><p className="text-muted">{t('dashboard.reports.subtitle')}</p>
    <div className="fg-filter-row" style={{ margin: '18px 0' }}>
      <input aria-label={t('dashboard.reports.search')} placeholder={t('dashboard.reports.search')} value={search} onChange={(e) => setSearch(e.target.value)} />
      <select aria-label={t('dashboard.reports.filterProblem')} value={problem} onChange={(e) => setProblem(e.target.value)}><option value="">{t('dashboard.reports.filterProblem')}: {t('common.all')}</option>{PROBLEMS.map((value) => <option key={value} value={value}>{t(PROBLEM_TRANSLATION_KEYS[value])}</option>)}</select>
      <select aria-label={t('dashboard.reports.filterSeverity')} value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="">{t('dashboard.reports.filterSeverity')}: {t('common.all')}</option>{Object.keys(severityRank).map((value) => <option key={value} value={value}>{t(`common.severityLevel.${value.toLowerCase()}`)}</option>)}</select>
      <select aria-label={t('dashboard.reports.filterZone')} value={zone} onChange={(e) => setZone(e.target.value)}><option value="">{t('dashboard.reports.filterZone')}: {t('common.all')}</option>{zones.map((value) => <option key={value} value={value}>{value}</option>)}</select>
      <select aria-label={t('dashboard.reports.filterStatus')} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">{t('dashboard.reports.filterStatus')}: {t('common.all')}</option>{['pending', 'confirmed', 'dismissed'].map((value) => <option key={value}>{value}</option>)}</select>
      <Button variant="ghost" size="sm" onClick={clear}>{t('common.clearFilters')}</Button>
    </div>
    {loadError && <Alert variant="error" title={t('errors.loadFailed')}><Button size="sm" onClick={() => { setLoading(true); setLoadError(false); setLoadAttempt((attempt) => attempt + 1); }}>{t('common.retry')}</Button></Alert>}
    {loading ? <Skeleton variant="block" /> : loadError ? null : filtered.length ? <>
      <div className="fg-table-wrap"><table className="fg-table"><thead><tr>{headers.map(([key, label]) => <th key={key}><button type="button" onClick={() => toggleSort(key)}>{t(label)} {sort.key === key ? (sort.direction === 'asc' ? '↑' : '↓') : ''}</button></th>)}<th>{t('common.status')}</th><th>{t('common.actions')}</th></tr></thead><tbody>{rows}</tbody></table></div>
      <div className="fg-report-cards fg-grid" style={{ marginTop: 14 }}>{pageItems.map((report) => <Card key={report.id}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}><Badge label={`${t('common.zone')} ${report.zone}`} /><Badge label={t(`common.${report.status}`)} /></div><h3>{t(PROBLEM_TRANSLATION_KEYS[report.problem] || 'common.unknown')}</h3><div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}><RiskBadge level={report.severity} /><span>{report.confidence == null ? t('common.unknown') : `${report.confidence}%`}</span></div><p>{new Date(report.date).toLocaleDateString()}</p><div style={{ display: 'flex', gap: 8 }}><Button size="sm" onClick={() => setPendingAction({ id: report.id, action: 'confirm' })}>{t('dashboard.reports.confirmAction')}</Button><Button size="sm" variant="ghost" onClick={() => setPendingAction({ id: report.id, action: 'dismiss' })}>{t('dashboard.reports.dismissAction')}</Button></div></Card>)}</div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16, marginTop: 18 }}><Button variant="secondary" disabled={page <= 1} aria-label={t('dashboard.reports.paginationPrev')} onClick={() => setPage((p) => Math.max(1, p - 1))}>‹</Button><span>{t('dashboard.reports.pagination', { page, total: totalPages })}</span><Button variant="secondary" disabled={page >= totalPages} aria-label={t('dashboard.reports.paginationNext')} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>›</Button></div>
    </> : <EmptyState title={t('dashboard.reports.empty')} message={t('dashboard.reports.emptyMessage')} />}
    <Modal isOpen={Boolean(pendingAction)} onClose={() => setPendingAction(null)} title={t(pendingAction?.action === 'confirm' ? 'dashboard.reports.confirmModalTitle' : 'dashboard.reports.dismissModalTitle')}>
      <p>{t(pendingAction?.action === 'confirm' ? 'dashboard.reports.confirmModalMessage' : 'dashboard.reports.dismissModalMessage')}</p>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}><Button variant="ghost" onClick={() => setPendingAction(null)}>{t(pendingAction?.action === 'confirm' ? 'dashboard.reports.confirmModalNo' : 'dashboard.reports.dismissModalNo')}</Button><Button variant={pendingAction?.action === 'confirm' ? 'primary' : 'danger'} onClick={act}>{t(pendingAction?.action === 'confirm' ? 'dashboard.reports.confirmModalYes' : 'dashboard.reports.dismissModalYes')}</Button></div>
    </Modal>
  </main>;
}
