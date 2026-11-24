import { useNavigate } from 'react-router-dom';
import Button from '../components/Button.jsx';
import { useTranslation } from '../i18n/useTranslation.js';

export default function NotFoundPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return <main style={{ minHeight: '100vh', display: 'grid', alignContent: 'center', justifyItems: 'center', gap: 12, padding: 24, textAlign: 'center' }}>
    <svg aria-hidden="true" viewBox="0 0 100 100" width="100" height="100" fill="none" stroke="var(--color-primary)" strokeWidth="3"><path d="M50 46C34 31 44 14 53 18c13 6 8 18-3 28Zm0 0c-1-20 18-25 23-16 6 10-7 19-23 16Zm0 0c17-12 31 1 24 11-7 10-19 4-24-11Zm0 0c15 16 3 31-7 27-11-4-7-21 7-27Zm0 0c-20 7-29-10-21-19 8-8 21 0 21 19Zm0 0v41" /></svg>
    <h1 style={{ fontSize: '4rem', margin: 0 }}>404</h1><h2>{t('notFound.title')}</h2><p>{t('notFound.message')}</p><Button onClick={() => navigate('/')}>{t('notFound.backHome')}</Button>
  </main>;
}
