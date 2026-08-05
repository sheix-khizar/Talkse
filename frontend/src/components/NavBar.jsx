import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Search, 
  Bell, 
  Calendar, 
  LogOut, 
  LayoutDashboard, 
  PhoneCall, 
  Sliders, 
  PieChart, 
  CalendarCheck, 
  Radio,
  Sparkles,
  Bot
} from 'lucide-react';
import { useAuth, useUser } from '@clerk/clerk-react';
import './NavBar.css';

export default function NavBar() {
  const location = useLocation();
  const { signOut } = useAuth();
  const { user } = useUser();

  const tabs = [
    { id: 'overview', label: 'Overview', path: '/overview', icon: LayoutDashboard },
    { id: 'calls', label: 'Calls', path: '/calls', icon: PhoneCall },
    { id: 'calendar', label: 'Calendar', path: '/calendar', icon: Calendar },
    { id: 'settings', label: 'Settings', path: '/settings', icon: Sliders },
    { id: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: PieChart },
    { id: 'appointments', label: 'Appointments', path: '/appointments', icon: CalendarCheck },
    { id: 'live', label: 'Live Call', path: '/', icon: Radio, isLivePulse: true }
  ];

  return (
    <header className="navbar-container-3d">
      <div className="navbar-inner-3d">
        {/* Brand Logo & Title */}
        <Link to="/" className="navbar-brand-3d">
          <div className="brand-logo-3d">
            <Bot size={22} className="bot-icon" />
            <div className="logo-sparkle">
              <Sparkles size={10} />
            </div>
          </div>
          <div className="brand-text">
            <h1 className="brand-title-3d">
              TALKSE <span className="title-accent-3d">AI</span>
            </h1>
            <span className="brand-subtitle-3d">CLINIC COMPASS</span>
          </div>
        </Link>



        {/* Navigation Tabs Bar */}
        <nav className="navbar-tabs-3d">
          {tabs.map((tab) => {
            const isActive = location.pathname === tab.path;
            const Icon = tab.icon;

            return (
              <Link
                key={tab.id}
                to={tab.path}
                className={`tab-btn-3d ${isActive ? 'active-tab-3d' : ''} ${tab.isLivePulse ? 'live-tab-3d' : ''}`}
              >
                <div className="tab-icon-wrapper">
                  <Icon size={16} className="tab-icon" />
                  {tab.isLivePulse && <span className="live-dot-pulse"></span>}
                </div>
                <span>{tab.label}</span>
                {isActive && <div className="tab-glow-bar" />}
              </Link>
            );
          })}
        </nav>

        {/* Right User Utilities */}
        <div className="navbar-utilities-3d">
          {/* Search Input */}
          <div className="search-bar-3d">
            <Search size={15} className="search-icon-3d" />
            <input type="text" placeholder="Search clinic..." />
          </div>

          {/* Notifications Bell */}
          <button className="icon-btn-3d bell-btn" title="Notifications">
            <Bell size={17} />
            <span className="bell-badge-3d">1</span>
          </button>

          {/* User Profile Card */}
          <div className="user-profile-3d">
            <div className="avatar-wrapper-3d">
              <img
                src={user?.imageUrl || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80"}
                alt="User avatar"
                className="user-avatar-3d"
              />
              <span className="avatar-status-dot"></span>
            </div>
            <div className="user-details-3d">
              <span className="user-name-3d">
                {user?.fullName || user?.primaryEmailAddress?.emailAddress?.split('@')[0] || 'Admin'}
              </span>
              <span className="user-role-badge">ADMIN</span>
            </div>
          </div>

          {/* Logout Button */}
          <button className="icon-btn-3d logout-btn-3d" onClick={() => signOut()} title="Sign Out">
            <LogOut size={17} />
          </button>
        </div>
      </div>
    </header>
  );
}
