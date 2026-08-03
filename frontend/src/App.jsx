import React from 'react';
import LiveCallView from './pages/LiveCallView';
import LoginPage from './auth/LoginPage';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { TenantProvider } from './context/TenantContext';
import './theme/tokens.css';

function MainApp() {
  const { user } = useAuth();

  if (!user || !user.isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <TenantProvider>
      <LiveCallView />
    </TenantProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
