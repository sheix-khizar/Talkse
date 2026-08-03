import React, { createContext, useContext, useState } from 'react';

const TenantContext = createContext();

export const TENANTS = [
  { id: '042', name: 'Lumina Aesthetics', domain: 'lumina-demo.com' },
  { id: '043', name: 'SkinSpirit Medical Spa', domain: 'skinspirit.com' },
  { id: '044', name: 'Aesthetic Wellness Clinic', domain: 'wellness-demo.com' }
];

export function TenantProvider({ children }) {
  const [selectedTenant, setSelectedTenant] = useState(TENANTS[0]);

  return (
    <TenantContext.Provider value={{ selectedTenant, setSelectedTenant, tenants: TENANTS }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
}
