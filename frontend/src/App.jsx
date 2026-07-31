import React from 'react';
import { SignedIn, SignedOut } from '@clerk/clerk-react';
import LiveCallView from './pages/LiveCallView';
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
          <LiveCallView />
        </TenantProvider>
      </SignedIn>
    </>
  );
}
