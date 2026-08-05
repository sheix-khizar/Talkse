import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { fetchAppointments } from '../api/appointments';
import { 
  Calendar, 
  Clock, 
  User, 
  Search, 
  Filter, 
  CheckCircle2, 
  Sparkles, 
  Stethoscope, 
  RefreshCw,
  ChevronRight,
  TrendingUp,
  SlidersHorizontal,
  XCircle
} from 'lucide-react';
import './AppointmentsPage.css';

// Helper to format service names cleanly
const formatService = (serviceId) => {
  if (!serviceId) return 'General Consultation';
  const clean = serviceId.replace(/^svc_/, '').replace(/_/g, ' ');
  return clean.charAt(0).toUpperCase() + clean.slice(1);
};

// Helper to format provider names
const formatProvider = (providerId) => {
  if (!providerId) return 'Dr. Assigned';
  if (providerId === 'prov_001') return 'Dr. Sarah (prov_001)';
  if (providerId === 'prov_003') return 'Dr. Alex (prov_003)';
  if (providerId === 'prov_004') return 'Dr. Elena (prov_004)';
  return providerId;
};

// Helper to extract patient initials for 3D avatar
const getInitials = (name) => {
  if (!name || name === 'Unknown') return 'PA';
  const parts = name.trim().split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
};

// Color generator for patient avatar gradients
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

export default function AppointmentsPage() {
  const { getToken } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [serviceFilter, setServiceFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selectedAppointment, setSelectedAppointment] = useState(null);

  // 3D Card Tilt Effect Ref
  const tableCardRef = useRef(null);

  const loadData = () => {
    setLoading(true);
    setError(null);
    fetchAppointments(getToken)
      .then(data => {
        setAppointments(data || []);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [getToken]);

  // Handle 3D perspective tilt on table card hover
  const handleMouseMove = (e) => {
    if (!tableCardRef.current) return;
    const rect = tableCardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    const rotateX = (-y / rect.height) * 4; // subtle X tilt
    const rotateY = (x / rect.width) * 4;   // subtle Y tilt
    tableCardRef.current.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
  };

  const handleMouseLeave = () => {
    if (!tableCardRef.current) return;
    tableCardRef.current.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
  };

  // Filter appointments based on search and dropdown filters
  const filteredAppointments = appointments.filter(app => {
    const patientName = app.caller_name || 'Unknown';
    const serviceName = app.service_id || '';
    const providerName = app.provider_id || '';
    
    const matchesSearch = patientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          serviceName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          providerName.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesService = serviceFilter === 'ALL' || app.service_id === serviceFilter;
    const matchesStatus = statusFilter === 'ALL' || app.status === statusFilter;

    return matchesSearch && matchesService && matchesStatus;
  });

  // Extract unique services for filter dropdown
  const uniqueServices = Array.from(new Set(appointments.map(a => a.service_id).filter(Boolean)));

  // Calculate summary stats
  const totalCount = appointments.length;
  const confirmedCount = appointments.filter(a => a.status === 'confirmed').length;
  const pendingCount = appointments.filter(a => a.status === 'pending').length;

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
          <p className="loading-text">Loading 3D Booking Records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container appointments-3d-wrapper">
      {/* ── Page Header ── */}
      <div className="page-header-3d">
        <div className="header-title-group">
          <div className="header-icon-glow">
            <Calendar className="icon-3d" size={28} />
          </div>
          <div>
            <h2 className="page-title-3d">Appointments Directory</h2>
            <p className="page-subtitle-3d">Real-time patient bookings, AI session logs & status overview</p>
          </div>
        </div>

        <button className="refresh-btn-3d" onClick={loadData} title="Refresh Appointments">
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          <span>Sync Data</span>
        </button>
      </div>

      {error && (
        <div className="error-banner-3d">
          <XCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* ── Summary Stats Cards (3D Glassmorphism Grid) ── */}
      <div className="stats-grid-3d">
        <div className="stat-card-3d card-teal">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Total Bookings</span>
              <h3 className="stat-value">{totalCount}</h3>
              <span className="stat-badge"><TrendingUp size={12} /> Active Sync</span>
            </div>
            <div className="stat-icon-wrapper">
              <Calendar size={24} />
            </div>
          </div>
          <div className="card-3d-shine"></div>
        </div>

        <div className="stat-card-3d card-emerald">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Confirmed Appointments</span>
              <h3 className="stat-value">{confirmedCount}</h3>
              <span className="stat-badge green-glow"><CheckCircle2 size={12} /> 100% Validated</span>
            </div>
            <div className="stat-icon-wrapper green-bg">
              <CheckCircle2 size={24} />
            </div>
          </div>
          <div className="card-3d-shine"></div>
        </div>

        <div className="stat-card-3d card-cyan">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Pending / In-Review</span>
              <h3 className="stat-value">{pendingCount}</h3>
              <span className="stat-badge cyan-glow"><Clock size={12} /> Queue Status</span>
            </div>
            <div className="stat-icon-wrapper cyan-bg">
              <Clock size={24} />
            </div>
          </div>
          <div className="card-3d-shine"></div>
        </div>

        <div className="stat-card-3d card-purple">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Available Services</span>
              <h3 className="stat-value">{uniqueServices.length || 1}</h3>
              <span className="stat-badge purple-glow"><Sparkles size={12} /> AI Categorized</span>
            </div>
            <div className="stat-icon-wrapper purple-bg">
              <Stethoscope size={24} />
            </div>
          </div>
          <div className="card-3d-shine"></div>
        </div>
      </div>

      {/* ── Search & Filter Control Bar ── */}
      <div className="controls-bar-3d">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            className="search-input-3d"
            placeholder="Search by patient name, service, or provider..."
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
            <Filter size={14} className="filter-icon" />
            <select
              className="select-3d"
              value={serviceFilter}
              onChange={(e) => setServiceFilter(e.target.value)}
            >
              <option value="ALL">All Services</option>
              {uniqueServices.map(svc => (
                <option key={svc} value={svc}>{formatService(svc)}</option>
              ))}
            </select>
          </div>

          <div className="select-wrapper-3d">
            <SlidersHorizontal size={14} className="filter-icon" />
            <select
              className="select-3d"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="confirmed">Confirmed</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── Main 3D Elevated Table Container ── */}
      <div 
        className="table-card-3d"
        ref={tableCardRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <div className="table-top-bar">
          <div className="table-badge-tag">
            <span className="dot-pulse"></span>
            <span>Showing {filteredAppointments.length} of {appointments.length} Bookings</span>
          </div>
        </div>

        <div className="table-scroll-container">
          <table className="data-table-3d">
            <thead>
              <tr>
                <th>Patient Name</th>
                <th>Service Booked</th>
                <th>Assigned Provider</th>
                <th>Date & Time</th>
                <th>Booking Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAppointments.length === 0 ? (
                <tr>
                  <td colSpan="6" className="empty-state-3d">
                    <div className="empty-content">
                      <div className="empty-icon-3d">
                        <Calendar size={42} />
                      </div>
                      <h4>No Appointments Found</h4>
                      <p>No matching patient bookings found for your current search/filter criteria.</p>
                      {(searchTerm || serviceFilter !== 'ALL' || statusFilter !== 'ALL') && (
                        <button 
                          className="reset-filter-btn" 
                          onClick={() => { setSearchTerm(''); setServiceFilter('ALL'); setStatusFilter('ALL'); }}
                        >
                          Reset Filters
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredAppointments.map((a) => {
                  const patientName = a.caller_name || 'Unknown Patient';
                  const initials = getInitials(patientName);
                  const isConfirmed = a.status === 'confirmed';

                  return (
                    <tr 
                      key={a.id} 
                      className={`table-row-3d ${selectedAppointment?.id === a.id ? 'row-selected' : ''}`}
                      onClick={() => setSelectedAppointment(a)}
                    >
                      {/* Patient Avatar & Name */}
                      <td className="patient-cell">
                        <div className="patient-flex">
                          <div 
                            className="patient-avatar-3d"
                            style={{ background: getAvatarGradient(patientName) }}
                          >
                            {initials}
                          </div>
                          <div className="patient-details">
                            <span className="patient-name">{patientName}</span>
                            <span className="patient-id">Ref: #{String(a.id).slice(0, 8)}</span>
                          </div>
                        </div>
                      </td>

                      {/* Service Badge */}
                      <td>
                        <span className="service-badge-3d">
                          <Sparkles size={13} className="badge-sparkle" />
                          <span>{formatService(a.service_id)}</span>
                        </span>
                      </td>

                      {/* Provider Badge */}
                      <td>
                        <div className="provider-chip-3d">
                          <User size={13} />
                          <span>{formatProvider(a.provider_id)}</span>
                        </div>
                      </td>

                      {/* Date & Time */}
                      <td className="datetime-cell">
                        <div className="datetime-flex">
                          <Calendar size={14} className="cell-icon" />
                          <span>
                            {new Date(a.scheduled_start).toLocaleString(undefined, { 
                              weekday: 'short', 
                              month: 'short', 
                              day: 'numeric', 
                              hour: 'numeric', 
                              minute: '2-digit'
                            })}
                          </span>
                        </div>
                      </td>

                      {/* Status Dot Pill */}
                      <td>
                        <div className={`status-pill-3d ${isConfirmed ? 'status-confirmed' : 'status-pending'}`}>
                          <span className="status-dot-3d" />
                          <span className="capitalize-text">{a.status || 'confirmed'}</span>
                        </div>
                      </td>

                      {/* Action Button */}
                      <td className="text-right">
                        <button className="action-btn-3d" title="View Booking Details">
                          <span>Details</span>
                          <ChevronRight size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
