/**
 * AlertContext — provides backend alerts and local read state.
 */

import { createContext, useCallback, useContext, useEffect, useState, useMemo } from 'react';
import { getAlerts } from '../api.js';

const AlertContext = createContext({
  alerts: [],
  unreadCount: 0,
  loadError: false,
  refreshAlerts: async () => {},
  markRead: () => {},
  markAllRead: () => {},
});

export function AlertProvider({ children }) {
  const [alerts, setAlerts] = useState([]);
  const [loadError, setLoadError] = useState(false);

  const refreshAlerts = useCallback(async () => {
    try {
      const items = await getAlerts();
      setAlerts((previous) => {
        const readById = new Map(previous.map((alert) => [alert.id, alert.read]));
        return items.map((alert) => ({ ...alert, read: readById.get(alert.id) ?? alert.read }));
      });
      setLoadError(false);
    } catch (error) {
      console.error('[AlertContext] Could not load alerts', error);
      setLoadError(true);
    }
  }, []);

  useEffect(() => { refreshAlerts(); }, [refreshAlerts]);

  const unreadCount = useMemo(
    () => alerts.filter((a) => !a.read).length,
    [alerts]
  );

  const markRead = (id) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, read: true } : a))
    );
  };

  const markAllRead = () => {
    setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
  };

  return (
    <AlertContext.Provider value={{ alerts, unreadCount, loadError, refreshAlerts, markRead, markAllRead }}>
      {children}
    </AlertContext.Provider>
  );
}

/** Convenience hook */
export function useAlerts() {
  return useContext(AlertContext);
}
