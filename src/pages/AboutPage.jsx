import { Link } from 'react-router-dom';
import Header from '../components/Header.jsx';
import Card from '../components/Card.jsx';
import { PROBLEMS, PROBLEM_TRANSLATION_KEYS } from '../config.js';
import { useTranslation } from '../i18n/useTranslation.js';

export default function AboutPage() {
  const { t } = useTranslation();
  return <><Header /><main className="fg-page"><h1>{t('about.title')}</h1><p>{t('about.intro')}</p><Card style={{ margin: '24px 0', background: 'var(--color-accent-tint)' }}><strong>{t('about.disclaimer')}</strong></Card><h2>{t('about.howItWorks')}</h2><ul>{PROBLEMS.map((problem) => <li key={problem}>{t(PROBLEM_TRANSLATION_KEYS[problem])}</li>)}</ul><h2>{t('about.privacy')}</h2><p>{t('about.privacyDetail')}</p><Link to="/">{t('about.backHome')}</Link></main></>;
}
