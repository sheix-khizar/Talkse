import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { fetchAppointments } from '../api/appointments';
import { 
  Calendar as CalendarIcon, 
  Clock, 
  User, 
  Sparkles, 
  CheckCircle2, 
  Search, 
  RefreshCw, 
  CalendarDays,
  Tag,
  XCircle,
  SlidersHorizontal,
  ChevronRight
} from 'lucide-react';
import './CalendarPage.css';

// Helper to format service names cleanly
const formatService = (serviceId) => {
  if (!serviceId) return 'General Consultation';
  const clean = serviceId.replace(/^svc_/, '').replace(/_/g, ' ');
  return clean.charAt(0).toUpperCase() + clean.slice(1);
};

// Helper to format provider names
const formatProvider = (providerId) => {
  if (!providerId) return 'Dr. Assigned';
  if (providerId === 'prov_001') return 'Dr. Sarah';
  if (providerId === 'prov_003') return 'Dr. Alex';
  if (providerId === 'prov_004') return 'Dr. Elena';
  return providerId;
};

// Helper for 3D patient avatar initials
const getInitials = (name) => {
  if (!name || name === 'Unknown') return 'PA';
  const parts = name.trim().split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
};

// Color generator for 3D patient avatars
const getAvatarGradient = (name) => {
  const gradients = [
    'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    'linear-gradient(135deg, #0d9488 0%, #0891b2 100%)',
    'linear-gradient(135deg, #ec4899 0%, #d946ef 100%)',
    'linear-gradient(135deg, #f59e0b 0%, #ea580c 100%)',
    'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
  ];
  let charSum = 0;
  for (let i = 0; i < (name || '').length; i++) charSum += name.charCodeAt(i);
  return gradients[charSum % gradients.length];
};

export default function CalendarPage() {
  const { getToken } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedService, setSelectedService] = useState('ALL');

  const loadData = () => {
    setLoading(true);
    setError(null);
    fetchAppointments(getToken)
      .then(data => {
        setAppointments(data || []);
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [getToken]);

  // Filter appointments by search & service selection
  const filteredAppointments = appointments.filter(a => {
    const patientName = a.caller_name || 'Unknown';
    const serviceName = a.service_id || '';
    const matchesSearch = patientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          serviceName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesService = selectedService === 'ALL' || a.service_id === selectedService;
    return matchesSearch && matchesService;
  });

  // Group appointments by formatted date
  const grouped = filteredAppointments.reduce((acc, appt) => {
    const dateObj = new Date(appt.scheduled_start);
    const dateKey = dateObj.toLocaleDateString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });

    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(appt);
    return acc;
  }, {});

  // Extract unique services
  const uniqueServices = Array.from(new Set(appointments.map(a => a.service_id).filter(Boolean)));

  if (loading) {
    return (
      <div className="page-container flex-center">
        <div className="glass-loader-card">
          <div className="cube-loader">
            <div className="cube-face cube-front"></div>
            <div className="cube-face cube-back"></div>
            <div className="cube-face cube-right"></div>
            <div className="cube-face cube-left"></div>
            <div className="cube-face cube-top"></div>
            <div className="cube-face cube-bottom"></div>
          </div>
          <p className="loading-text">Loading 3D Booking Calendar...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container calendar-3d-wrapper">
      {/* ── Page Header ── */}
      <div className="page-header-3d">
        <div className="header-title-group">
          <div className="header-icon-glow">
            <CalendarDays className="icon-3d" size={28} />
          </div>
          <div>
            <h2 className="page-title-3d">Interactive Booking Calendar</h2>
            <p className="page-subtitle-3d">Visual timeline of upcoming clinic appointments & patient slots</p>
          </div>
        </div>

        <button className="refresh-btn-3d" onClick={loadData} title="Sync Calendar">
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          <span>Sync Schedule</span>
        </button>
      </div>

      {error && (
        <div className="error-banner-3d">
          <XCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* ── Summary Bar ── */}
      <div className="calendar-summary-bar-3d">
        <div className="summary-item-3d">
          <span className="summary-label">Scheduled Days</span>
          <span className="summary-val">{Object.keys(grouped).length}</span>
        </div>
        <div className="summary-item-3d">
          <span className="summary-label">Total Bookings</span>
          <span className="summary-val">{filteredAppointments.length}</span>
        </div>
        <div className="summary-item-3d">
          <span className="summary-label">Active Services</span>
          <span className="summary-val">{uniqueServices.length}</span>
        </div>
      </div>

      {/* ── Controls & Filter Bar ── */}
      <div className="controls-bar-3d">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            className="search-input-3d"
            placeholder="Search patient name or service..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button className="clear-search-btn" onClick={() => setSearchTerm('')}>
              <XCircle size={16} />
            </button>
          )}
        </div>

        <div className="filter-group">
          <div className="select-wrapper-3d">
            <SlidersHorizontal size={14} className="filter-icon" />
            <select
              className="select-3d"
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
            >
              <option value="ALL">All Services</option>
              {uniqueServices.map(svc => (
                <option key={svc} value={svc}>{formatService(svc)}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── 3D Calendar Grouped Schedule Grid ── */}
      <div className="calendar-grouped-container-3d">
        {Object.keys(grouped).length === 0 ? (
          <div className="empty-state-3d">
            <div className="empty-content">
              <div className="empty-icon-3d">
                <CalendarIcon size={42} />
              </div>
              <h4>No Calendar Bookings Found</h4>
              <p>No appointments match your search criteria for this timeframe.</p>
              {(searchTerm || selectedService !== 'ALL') && (
                <button 
                  className="reset-filter-btn" 
                  onClick={() => { setSearchTerm(''); setSelectedService('ALL'); }}
                >
                  Reset Search Filters
                </button>
              )}
            </div>
          </div>
        ) : (
          Object.keys(grouped).map(dateKey => {
            const dateAppts = grouped[dateKey];

            return (
              <div key={dateKey} className="calendar-day-card-3d">
                {/* 3D Date Banner */}
                <div className="day-header-3d">
                  <div className="day-title-flex">
                    <CalendarIcon size={18} className="day-icon" />
                    <h3 className="day-date-text">{dateKey}</h3>
                  </div>
                  <span className="day-count-badge">
                    <CheckCircle2 size={12} /> {dateAppts.length} {dateAppts.length === 1 ? 'Booking' : 'Bookings'}
                  </span>
                </div>

                {/* Appointment Tiles Grid */}
                <div className="tiles-grid-3d">
                  {dateAppts.map(a => {
                    const patientName = a.caller_name || 'Unknown Patient';
                    const initials = getInitials(patientName);
                    const formattedTime = new Date(a.scheduled_start).toLocaleTimeString([], {
                      hour: '2-digit', 
                      minute: '2-digit'
                    });

                    return (
                      <div key={a.id} className="appointment-tile-3d">
                        <div className="tile-top-bar">
                          <div className="time-chip-3d">
                            <Clock size={13} />
                            <span>{formattedTime}</span>
                          </div>
                          <div className="status-dot-glow" title="Status: Confirmed"></div>
                        </div>

                        <div className="tile-patient-flex">
                          <div 
                            className="tile-avatar-3d"
                            style={{ background: getAvatarGradient(patientName) }}
                          >
                            {initials}
                          </div>
                          <div>
                            <h4 className="tile-patient-name">{patientName}</h4>
                            <span className="tile-provider-text">
                              <User size={12} /> {formatProvider(a.provider_id)}
                            </span>
                          </div>
                        </div>

                        <div className="tile-footer">
                          <span className="tile-service-badge">
                            <Sparkles size={12} />
                            <span>{formatService(a.service_id)}</span>
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
