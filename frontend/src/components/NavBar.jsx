import React, { useState } from 'react';
import { Search, Bell, Calendar, ChevronDown, LogOut, Building } from 'lucide-react';
import { useTenant } from '../context/TenantContext';
import { useAuth } from '../auth/AuthContext';
import './NavBar.css';

export default function NavBar() {
  const [activeTab, setActiveTab] = useState('Appointments');
  const { selectedTenant, setSelectedTenant, tenants } = useTenant();
  const { user, logout } = useAuth();

  const tabs = [
    { id: 'Overview', label: 'Overview' },
    { id: 'Calls', label: 'Calls' },
    { id: 'Calendar', label: 'Calendar' },
    { id: 'Settings', label: 'Settings' },
    { id: 'Dashboard', label: 'Dashboard' },
    { id: 'Appointments', label: 'Appointments', isPill: true }
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
          if (tab.isPill) {
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab-pill ${activeTab === tab.id ? 'active' : ''}`}
              >
                <div className="tab-pill-icon">
                  <Calendar size={16} />
                </div>
                <span>{tab.label}</span>
              </button>
            );
          }
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-link ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.label}
              {activeTab === tab.id && <div className="active-indicator" />}
            </button>
          );
        })}
      </nav>

      {/* Right User Utilities */}
      <div className="navbar-utilities">
        {/* User profile */}
        <div className="user-profile">
          <img
            src={user?.avatar || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80"}
            alt="User avatar"
            className="user-avatar"
          />
          <div className="user-info">
            <span className="user-name">
              {user?.name || 'Luninsitara'}
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
        <button className="icon-button logout-btn" onClick={logout} title="Sign Out">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
