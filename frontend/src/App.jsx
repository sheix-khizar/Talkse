import React, { useState } from 'react';
import LiveCallView from './pages/LiveCallView';
import InferenceTester from './pages/InferenceTester';
import LoginPage from './auth/LoginPage';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { TenantProvider } from './context/TenantContext';
import './theme/tokens.css';

function MainApp() {
  const { user } = useAuth();
  const [view, setView] = useState('tester'); // Default to tester for testing purposes

  if (!user || !user.isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <TenantProvider>
      <div style={{ position: 'absolute', top: '10px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, background: 'rgba(0,0,0,0.5)', padding: '5px', borderRadius: '8px', display: 'flex', gap: '5px' }}>
        <button 
          onClick={() => setView('dashboard')}
          style={{ padding: '5px 10px', background: view === 'dashboard' ? '#38bdf8' : 'transparent', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Dashboard
        </button>
        <button 
          onClick={() => setView('tester')}
          style={{ padding: '5px 10px', background: view === 'tester' ? '#38bdf8' : 'transparent', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Inference Tester
        </button>
      </div>

      {view === 'dashboard' ? <LiveCallView /> : <InferenceTester />}
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
