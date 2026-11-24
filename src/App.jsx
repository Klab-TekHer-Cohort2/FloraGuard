/**
 * App.jsx — root component.
 *
 * Wraps the whole app in context providers and defines the React Router v6 route tree.
 * Pages are lazy-loaded to keep the initial bundle small.
 *
 * Route tree:
 *   /                 → WelcomePage
 *   /grower           → GrowerLayout
 *     index           → GrowerHome
 *     check           → CheckRoses
 *     map             → CommunityMap
 *     alerts          → GrowerAlerts
 *   /dashboard        → DashboardLayout
 *     index           → Overview
 *     map             → MapView
 *     reports         → Reports
 *     alerts          → DashboardAlerts
 *     settings        → Settings
 *   /about            → AboutPage
 *   *                 → NotFoundPage
 */

import { Suspense, lazy, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';

import { ThemeProvider } from './context/ThemeContext.jsx';
import { RoleProvider } from './context/RoleContext.jsx';
import { AlertProvider, useAlerts } from './context/AlertContext.jsx';
import { ToastProvider, useToast } from './components/ToastProvider.jsx';
import OfflineBanner from './components/OfflineBanner.jsx';
import Skeleton from './components/Skeleton.jsx';
import { syncQueuedReports } from './api.js';
import { useTranslation } from './i18n/useTranslation.js';

const WelcomePage = lazy(() => import('./pages/WelcomePage.jsx'));
const GrowerLayout = lazy(() => import('./pages/grower/GrowerLayout.jsx'));
const GrowerHome = lazy(() => import('./pages/grower/GrowerHome.jsx'));
const CheckRoses = lazy(() => import('./pages/grower/CheckRoses.jsx'));
const CommunityMap = lazy(() => import('./pages/grower/CommunityMap.jsx'));
const GrowerAlerts = lazy(() => import('./pages/grower/GrowerAlerts.jsx'));
const DashboardLayout = lazy(() => import('./pages/dashboard/DashboardLayout.jsx'));
const Overview = lazy(() => import('./pages/dashboard/Overview.jsx'));
const MapView = lazy(() => import('./pages/dashboard/MapView.jsx'));
const Reports = lazy(() => import('./pages/dashboard/Reports.jsx'));
const DashboardAlerts = lazy(() => import('./pages/dashboard/DashboardAlerts.jsx'));
const Settings = lazy(() => import('./pages/dashboard/Settings.jsx'));
const AboutPage = lazy(() => import('./pages/AboutPage.jsx'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.jsx'));

/** Full-screen loading fallback for Suspense */
function PageLoader() {
  return (
    <div
      role="status"
      aria-label="Loading"
      style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', padding: 24, background: 'var(--color-bg)' }}
    >
      <Skeleton variant="block" style={{ maxWidth: 420, height: 180 }} />
    </div>
  );
}

function QueuedReportSync() {
  const toast = useToast();
  const { refreshAlerts } = useAlerts();
  const { t } = useTranslation();

  useEffect(() => {
    let active = true;
    let syncing = false;
    const sync = async () => {
      if (!navigator.onLine || syncing) return;
      syncing = true;
      try {
        const count = await syncQueuedReports();
        if (count > 0) {
          await refreshAlerts();
          if (active) toast(t('grower.checkRoses.offlineSynced', { count }), 'success');
        }
      } catch (error) {
        console.error('[QueuedReportSync] Could not upload saved reports', error);
        if (active) toast(t('grower.checkRoses.offlineSyncFailed'), 'error');
      } finally {
        syncing = false;
      }
    };

    window.addEventListener('online', sync);
    sync();
    return () => {
      active = false;
      window.removeEventListener('online', sync);
    };
  }, [refreshAlerts, t, toast]);

  return null;
}

export default function App() {
  return (
    <ThemeProvider>
      <RoleProvider>
        <AlertProvider>
          <ToastProvider>
            <OfflineBanner />
            <QueuedReportSync />
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<WelcomePage />} />

                <Route path="/grower" element={<GrowerLayout />}>
                  <Route index element={<GrowerHome />} />
                  <Route path="check" element={<CheckRoses />} />
                  <Route path="map" element={<CommunityMap />} />
                  <Route path="alerts" element={<GrowerAlerts />} />
                </Route>

                <Route path="/dashboard" element={<DashboardLayout />}>
                  <Route index element={<Overview />} />
                  <Route path="map" element={<MapView />} />
                  <Route path="reports" element={<Reports />} />
                  <Route path="alerts" element={<DashboardAlerts />} />
                  <Route path="settings" element={<Settings />} />
                </Route>

                <Route path="/about" element={<AboutPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </Suspense>
          </ToastProvider>
        </AlertProvider>
      </RoleProvider>
    </ThemeProvider>
  );
}
