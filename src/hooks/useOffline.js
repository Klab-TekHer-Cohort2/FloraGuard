/**
 * useOffline — returns { isOffline } that tracks whether the browser
 * currently has no network connection.
 *
 * Reads navigator.onLine on mount and updates on window online/offline events.
 * Cleans up event listeners on unmount.
 */

import { useEffect, useState } from 'react';

export function useOffline() {
  const [isOffline, setIsOffline] = useState(
    typeof navigator !== 'undefined' ? !navigator.onLine : false
  );

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { isOffline };
}
