/**
 * RoleContext — provides { role, setRole } to the whole app.
 *
 * role: 'grower' | 'manager' | null
 * Persists to localStorage key "fg_role".
 */

import { createContext, useContext, useState } from 'react';

const STORAGE_KEY = 'fg_role';
const VALID_ROLES = ['grower', 'manager'];

const RoleContext = createContext({
  role: null,
  setRole: () => {},
});

export function RoleProvider({ children }) {
  const [role, setRoleState] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return VALID_ROLES.includes(stored) ? stored : null;
    } catch {
      return null;
    }
  });

  const setRole = (newRole) => {
    const validRole = VALID_ROLES.includes(newRole) ? newRole : null;
    setRoleState(validRole);
    try {
      if (validRole) {
        localStorage.setItem(STORAGE_KEY, validRole);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // localStorage unavailable
    }
  };

  return (
    <RoleContext.Provider value={{ role, setRole }}>
      {children}
    </RoleContext.Provider>
  );
}

/** Convenience hook */
export function useRole() {
  return useContext(RoleContext);
}
