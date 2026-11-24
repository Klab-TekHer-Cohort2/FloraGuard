/**
 * useTranslation — custom React hook for FloraGuard i18n.
 *
 * Usage:
 *   const { t, lang, setLang } = useTranslation();
 *   t('common.riskLevel.high') // => "High risk"
 *   setLang('rw')              // => switches to Kinyarwanda, persists to localStorage
 */

import { useState, useCallback, useEffect } from 'react';
import en from './en.json';
import rw from './rw.json';

const LOCALES = { en, rw };
const STORAGE_KEY = 'fg_lang';
const DEFAULT_LANG = 'en';

/**
 * Resolves a dot-separated key path against a nested object.
 * Returns `undefined` if the key does not exist.
 *
 * @param {object} obj
 * @param {string} key - e.g. "common.riskLevel.high"
 * @returns {string|undefined}
 */
function resolvePath(obj, key) {
  return key.split('.').reduce((acc, part) => {
    if (acc == null || typeof acc !== 'object') return undefined;
    return acc[part];
  }, obj);
}

export function useTranslation() {
  const [lang, setLangState] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored && LOCALES[stored] ? stored : DEFAULT_LANG;
    } catch {
      return DEFAULT_LANG;
    }
  });

  useEffect(() => {
    const syncLanguage = (event) => {
      if (event.detail && LOCALES[event.detail]) {
        setLangState(event.detail);
        return;
      }
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored && LOCALES[stored]) setLangState(stored);
      } catch {
        // Keep the current in-memory language when storage is unavailable.
      }
    };
    window.addEventListener('fg-language-change', syncLanguage);
    return () => window.removeEventListener('fg-language-change', syncLanguage);
  }, []);

  const setLang = useCallback((code) => {
    if (!LOCALES[code]) return;
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      // localStorage unavailable — proceed in-memory
    }
    setLangState(code);
    if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('fg-language-change', { detail: code }));
  }, []);

  /**
   * Translate a key.
   * Falls back to the English value, then to the key itself if still missing.
   *
   * Supports simple interpolation: t('common.hoursAgo', { n: 3 }) => "3 h ago"
   *
   * @param {string} key
   * @param {object} [vars] - interpolation variables
   * @returns {string}
   */
  const t = useCallback(
    (key, vars) => {
      const dict = LOCALES[lang] ?? LOCALES[DEFAULT_LANG];
      let value = resolvePath(dict, key);

      // Fall back to English if the current lang doesn't have this key
      if (value === undefined || value === null) {
        value = resolvePath(LOCALES[DEFAULT_LANG], key);
      }

      // Fall back to the key itself
      if (value === undefined || value === null) {
        return key;
      }

      // Interpolate {{variable}} placeholders
      if (vars && typeof value === 'string') {
        return value.replace(/\{\{(\w+)\}\}/g, (_, name) =>
          vars[name] !== undefined ? String(vars[name]) : `{{${name}}}`
        );
      }

      return String(value);
    },
    [lang]
  );

  return { t, lang, setLang };
}
