import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Search, Bell, Calendar, ChevronDown, LogOut, Building } from 'lucide-react';
import { useTenant } from '../context/TenantContext';
import { useAuth, useUser } from '@clerk/clerk-react';
import './NavBar.css';

export default function NavBar() {
  const location = useLocation();
  const { selectedTenant, setSelectedTenant, tenants } = useTenant();
  const { signOut } = useAuth();
  const { user } = useUser();

  const tabs = [
    { id: 'overview', label: 'Overview', path: '/overview' },
    { id: 'calls', label: 'Calls', path: '/calls' },
    { id: 'calendar', label: 'Calendar', path: '/calendar' },
    { id: 'settings', label: 'Settings', path: '/settings' },
    { id: 'dashboard', label: 'Dashboard', path: '/dashboard' },
    { id: 'appointments', label: 'Appointments', path: '/appointments', isPill: true },
    { id: 'live', label: 'Live Call', path: '/' }
  ];

  return (
    <header className="navbar-container">
      {/* Brand Logo & Tagline */}
      <div className="navbar-brand">
        <div className="brand-logo-icon">
          <span>AI</span>
        </div>
        <div className="brand-text">
          <h1 className="brand-title">TALKSE</h1>
          <span className="brand-subtitle">AI RECEPCIONIST - CLINIC COMPASS</span>
        </div>
      </div>

      {/* Tenant Selector Dropdown */}
      <div className="tenant-selector-wrapper">
        <Building size={16} className="tenant-icon" />
        <select
          className="tenant-select"
          value={selectedTenant.id}
          onChange={(e) => {
            const found = tenants.find((t) => t.id === e.target.value);
            if (found) setSelectedTenant(found);
          }}
        >
          {tenants.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} (ID: {t.id})
            </option>
          ))}
        </select>
      </div>

      {/* Center Navigation Tabs */}
      <nav className="navbar-tabs">
        {tabs.map((tab) => {
          const isActive = location.pathname === tab.path;
          if (tab.isPill) {
            return (
              <Link
                key={tab.id}
                to={tab.path}
                className={`tab-pill ${isActive ? 'active' : ''}`}
              >
                <div className="tab-pill-icon">
                  <Calendar size={16} />
                </div>
                <span>{tab.label}</span>
              </Link>
            );
          }
          return (
            <Link
              key={tab.id}
              to={tab.path}
              className={`tab-link ${isActive ? 'active' : ''}`}
            >
              {tab.label}
              {isActive && <div className="active-indicator" />}
            </Link>
          );
        })}
      </nav>

      {/* Right User Utilities */}
      <div className="navbar-utilities">
        {/* User profile */}
        <div className="user-profile">
          <img
            src={user?.imageUrl || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80"}
            alt="User avatar"
            className="user-avatar"
          />
          <div className="user-info">
            <span className="user-name">
              {user?.fullName || user?.primaryEmailAddress?.emailAddress || 'User'}
            </span>
            <span className="user-sub">{user?.role || 'ADMIN'}</span>
          </div>
        </div>

        {/* Notification Bell */}
        <button className="icon-button notification-bell" title="Notifications">
          <Bell size={18} />
          <span className="bell-badge">1</span>
        </button>

        {/* Search Bar */}
        <div className="search-bar">
          <Search size={16} className="search-icon" />
          <input type="text" placeholder="Search" />
        </div>

        {/* Logout Button */}
        <button className="icon-button logout-btn" onClick={() => signOut()} title="Sign Out">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
