import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { SignedIn, SignedOut, useAuth } from '@clerk/clerk-react';
import NavBar from './components/NavBar';
import LiveCallView from './pages/LiveCallView';
import AppointmentsPage from './pages/AppointmentsPage';
import CallsPage from './pages/CallsPage';
import DashboardPage from './pages/DashboardPage';
import OverviewPage from './pages/OverviewPage';
import CalendarPage from './pages/CalendarPage';
import SettingsPage from './pages/SettingsPage';
import InferenceTester from './pages/InferenceTester';
import LoginPage from './auth/LoginPage';
import { TenantProvider } from './context/TenantContext';
import './theme/tokens.css';

export default function App() {
  const [view, setView] = useState('dashboard');

  return (
    <>
      <SignedOut>
        <LoginPage />
      </SignedOut>
      <SignedIn>
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
          {view === 'dashboard' ? (
            <>
              <NavBar />
              <Routes>
                <Route path="/" element={<LiveCallView />} />
                <Route path="/appointments" element={<AppointmentsPage />} />
                <Route path="/calls" element={<CallsPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/overview" element={<OverviewPage />} />
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </>
          ) : (
            <InferenceTester />
          )}
        </TenantProvider>
      </SignedIn>
    </>
  );
}
export default function App() {
  return (
    <>
      <SignedOut>
        <LoginPage />
      </SignedOut>
      <SignedIn>
        <TenantProvider>
          <NavBar />
          <Routes>
            <Route path="/" element={<LiveCallView />} />
            <Route path="/appointments" element={<AppointmentsPage />} />
            <Route path="/calls" element={<CallsPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </TenantProvider>
      </SignedIn>
    </>
  );
}
