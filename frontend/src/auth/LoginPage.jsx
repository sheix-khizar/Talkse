import React from 'react';
import { SignIn } from '@clerk/clerk-react';

export default function LoginPage() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#f0f2f5' }}>
      <SignIn routing="hash" />
    </div>
  );
}
