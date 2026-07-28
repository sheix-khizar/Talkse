import React, { useState } from 'react';
import { useAuth } from './AuthContext';
import { Lock, User } from 'lucide-react';
import './LoginPage.css';

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('Luninsitara');
  const [password, setPassword] = useState('password');

  const handleSubmit = (e) => {
    e.preventDefault();
    login({ username, password });
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-logo-icon">AI</div>
          <h2 className="login-title">Talkse Platform</h2>
          <p className="login-sub">Sign in to access your clinic receptionist dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>Username or Email</label>
            <div className="input-wrapper">
              <User size={16} className="input-icon" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username..."
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Password</label>
            <div className="input-wrapper">
              <Lock size={16} className="input-icon" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password..."
                required
              />
            </div>
          </div>

          <button type="submit" className="btn-login">
            Sign In to Dashboard
          </button>
        </form>
      </div>
    </div>
  );
}
