import { useEffect, useRef, useState } from 'react';
import { Camera, ImagePlus, RotateCcw, Upload } from 'lucide-react';
import { LOW_CONFIDENCE_THRESHOLD, PROBLEM_TRANSLATION_KEYS } from '../../config.js';
import { queueReportOffline, submitReport } from '../../api.js';
import { useOffline } from '../../hooks/useOffline.js';
import { useTranslation } from '../../i18n/useTranslation.js';
import { useToast } from '../../components/ToastProvider.jsx';
import { useAlerts } from '../../context/AlertContext.jsx';
import Button from '../../components/Button.jsx';
import Card from '../../components/Card.jsx';
import Alert from '../../components/Alert.jsx';
import Modal from '../../components/Modal.jsx';
import SeverityMeter from '../../components/SeverityMeter.jsx';
import RiskBadge from '../../components/RiskBadge.jsx';
import Skeleton from '../../components/Skeleton.jsx';

async function compressImage(file) {
  const imageUrl = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = imageUrl;
    await image.decode();
    const scale = Math.min(1, 1280 / Math.max(image.width, image.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(image.width * scale);
    canvas.height = Math.round(image.height * scale);
    canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve, reject) => canvas.toBlob((result) => result ? resolve(result) : reject(new Error('Could not compress photo')), 'image/jpeg', 0.8));
    return blob;
  } finally {
    URL.revokeObjectURL(imageUrl);
  }
}

export default function CheckRoses() {
  const { t } = useTranslation();
  const toast = useToast();
  const { refreshAlerts } = useAlerts();
  const { isOffline } = useOffline();
  const inputRef = useRef(null);
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState(null);
  const [state, setState] = useState('idle');
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const selectFile = (file) => {
    if (!file || !['image/jpeg', 'image/png'].includes(file.type)) { toast(t('errors.invalidImage'), 'error'); return; }
    if (file.size > 10 * 1024 * 1024) { toast(t('errors.imageTooLarge'), 'error'); return; }
    setPhoto(file);
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setState('preview');
  };
  const reset = () => { setPhoto(null); setPreview(''); setResult(null); setErrorMessage(''); setState('idle'); };
  const analyse = async () => {
    if (!photo) return;
    setState('analysing');
    try {
      const compressed = await compressImage(photo);
      if (isOffline) {
        setResult({
          problem: 'Unknown',
          severity: 'Unknown',
          confidence: null,
          riskLevel: 'Unknown',
          riskReasons: [],
          advice: [],
          photo: compressed,
          submitted: false,
          offline: true,
        });
      } else {
        const report = await submitReport(compressed);
        setResult({ ...report, photo: compressed, submitted: true });
        await refreshAlerts();
      }
      setState('result');
    } catch (error) {
      console.error('[CheckRoses] Analysis failed', error);
      setErrorMessage(error instanceof Error ? error.message : t('grower.checkRoses.errorMessage'));
      setState('error');
    }
  };
  const share = async () => {
    if (!result?.photo) return;
    setSubmitting(true);
    try {
      if (isOffline) {
        await queueReportOffline(result.photo);
        toast(t('grower.checkRoses.offlineQueued'), 'success');
        reset();
      } else {
        const report = await submitReport(result.photo);
        setResult({ ...report, photo: result.photo, submitted: true });
        await refreshAlerts();
        toast(t('grower.checkRoses.submitSuccess'), 'success');
      }
    } catch (error) {
      console.error('[CheckRoses] Could not submit report', error);
      toast(error instanceof Error ? error.message : t('grower.checkRoses.submitError'), 'error');
    } finally { setSubmitting(false); }
  };
  const hasConfidence = result?.confidence != null && Number.isFinite(result.confidence);
  const needsReview = result && (!hasConfidence || result.confidence < LOW_CONFIDENCE_THRESHOLD || result.problem === 'Unknown');
  return <div className="fg-grid" style={{ gap: 18 }}>
    <div><h1>{t('grower.checkRoses.title')}</h1><p className="text-muted">{t('grower.checkRoses.uploadInstruction')}</p></div>
    {state === 'idle' && <Card className="fg-upload-area" onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); selectFile(event.dataTransfer.files?.[0]); }} style={{ padding: 32, textAlign: 'center', border: '2px dashed var(--color-primary)', background: 'var(--color-primary-tint)' }}>
      <Camera size={38} color="var(--color-primary)" /><h2>{t('grower.checkRoses.uploadTitle')}</h2><p>{t('grower.checkRoses.uploadDragDrop')}</p><Button onClick={(event) => { event.stopPropagation(); inputRef.current?.click(); }}><ImagePlus size={18} />{t('grower.checkRoses.uploadButton')}</Button><small style={{ display: 'block', marginTop: 12 }}>{t('grower.checkRoses.uploadFileSizeHint')}</small>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png" capture="environment" onChange={(event) => selectFile(event.target.files?.[0])} hidden aria-label={t('grower.checkRoses.uploadButton')} />
    </Card>}
    {state === 'preview' && <Card><img src={preview} alt={t('aria.photoPreview')} style={{ display: 'block', width: '100%', maxHeight: 420, objectFit: 'contain', borderRadius: 12, background: 'var(--color-bg)' }} /><div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 18 }}><Button onClick={analyse}><Upload size={18} />{t('grower.checkRoses.analyse')}</Button><Button variant="secondary" onClick={() => setConfirmDiscard(true)}><RotateCcw size={18} />{t('grower.checkRoses.retake')}</Button></div></Card>}
    {state === 'analysing' && <Card aria-live="polite"><p>{t('grower.checkRoses.analysing')}</p><p className="text-muted">{t('grower.checkRoses.analysingSubtitle')}</p><Skeleton variant="block" /></Card>}
    {state === 'error' && <Alert variant="error" title={t('grower.checkRoses.errorTitle')} message={errorMessage || t('grower.checkRoses.errorMessage')}><div style={{ marginTop: 12 }}><Button onClick={analyse}>{t('grower.checkRoses.errorRetry')}</Button></div></Alert>}
    {state === 'result' && result && <Card aria-label={t('grower.checkRoses.ariaResult')}>
      {result.submitted && <Alert variant="success" message={t('grower.checkRoses.submitSuccess')} />}
      {needsReview
        ? <Alert variant="warning"
            title={t(result.offline ? 'grower.checkRoses.offlineAnalysisTitle' : result.aiStatus === 'unavailable' ? 'grower.checkRoses.analysisUnavailableTitle' : 'grower.checkRoses.lowConfidenceTitle')}
            message={t(result.offline ? 'grower.checkRoses.offlineAnalysisMessage' : result.aiStatus === 'unavailable' ? 'grower.checkRoses.analysisUnavailableMessage' : 'grower.checkRoses.lowConfidenceMessage')} />
        : <h2>{t('grower.checkRoses.resultTitle')}</h2>}
      <p className="text-muted">{needsReview ? t('grower.checkRoses.lowConfidenceSuggestion') : t('common.problem')}</p>
      <h2 style={{ marginTop: 4 }}>{t(PROBLEM_TRANSLATION_KEYS[result.problem] || 'common.unknown')}</h2><RiskBadge level={result.severity} />
      {hasConfidence
        ? <div style={{ margin: '18px 0' }}><SeverityMeter value={result.confidence} label={t('grower.checkRoses.confidence')} ariaLabel={t('aria.confidenceMeter', { value: result.confidence })} /></div>
        : <p className="text-muted">{t('grower.checkRoses.confidenceUnavailable')}</p>}
      {result.riskLevel !== 'Unknown' && <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}><strong>{t('common.riskLevel.label')}</strong><RiskBadge level={result.riskLevel} /></div>}
      {result.riskReasons?.length > 0 && <><h3>{t('grower.checkRoses.advice')}</h3><ul>{result.riskReasons.map((item) => <li key={item}>{item}</li>)}</ul></>}
      <p className="text-muted">{t('grower.checkRoses.disclaimer')}</p>
      <div style={{ display: 'grid', gap: 10, marginTop: 18 }}>
        {!result.submitted && <Button loading={submitting} onClick={share}>{t(isOffline ? 'grower.checkRoses.offlineQueueButton' : 'grower.checkRoses.submitToMap')}</Button>}
        <Button variant="secondary" onClick={reset}>{t('grower.checkRoses.checkAnother')}</Button>
      </div>
    </Card>}
    <Modal isOpen={confirmDiscard} onClose={() => setConfirmDiscard(false)} title={t('grower.checkRoses.discardConfirm')}><div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}><Button variant="ghost" onClick={() => setConfirmDiscard(false)}>{t('grower.checkRoses.discardNo')}</Button><Button variant="danger" onClick={() => { setConfirmDiscard(false); reset(); }}>{t('grower.checkRoses.discardYes')}</Button></div></Modal>
  </div>;
}
