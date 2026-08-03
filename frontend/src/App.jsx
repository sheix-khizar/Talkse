import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { SignedIn, SignedOut } from '@clerk/clerk-react';
import NavBar from './components/NavBar';
import LiveCallView from './pages/LiveCallView';
import AppointmentsPage from './pages/AppointmentsPage';
import CallsPage from './pages/CallsPage';
import DashboardPage from './pages/DashboardPage';
import OverviewPage from './pages/OverviewPage';
import CalendarPage from './pages/CalendarPage';
import SettingsPage from './pages/SettingsPage';
import LoginPage from './auth/LoginPage';
import { TenantProvider } from './context/TenantContext';
import './theme/tokens.css';

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
