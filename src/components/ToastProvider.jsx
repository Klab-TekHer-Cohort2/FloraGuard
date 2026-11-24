import { createContext, useCallback, useContext, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import Toast from './Toast.jsx';

const ToastContext = createContext(() => {});

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);
  const addToast = useCallback((message, variant = 'info', duration = 3000) => {
    const id = ++nextId.current;
    setToasts((items) => [...items, { id, message, variant }]);
    window.setTimeout(() => setToasts((items) => items.filter((toast) => toast.id !== id)), duration);
    return id;
  }, []);
  const dismiss = (id) => setToasts((items) => items.filter((toast) => toast.id !== id));
  return (
    <ToastContext.Provider value={addToast}>
      {children}
      {createPortal(<div aria-label="Notifications" style={{ position: 'fixed', zIndex: 1200, left: '50%', bottom: 20, transform: 'translateX(-50%)', display: 'grid', gap: 8 }}>{toasts.map((toast) => <Toast key={toast.id} {...toast} onDismiss={() => dismiss(toast.id)} />)}</div>, document.body)}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
