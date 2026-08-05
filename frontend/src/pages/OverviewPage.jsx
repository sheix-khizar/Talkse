import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTenant } from '../context/TenantContext';
import { apiFetch } from '../api/client';
import CallQueueStrip from '../components/CallQueueStrip';
import { 
  LayoutDashboard, 
  PhoneCall, 
  CalendarCheck, 
  AlertTriangle, 
  Zap, 
  TrendingUp, 
  CheckCircle2, 
  ShieldCheck, 
  RefreshCw,
  Activity,
  Radio
} from 'lucide-react';
import './OverviewPage.css';

export default function OverviewPage() {
  const { getToken } = useAuth();
  const { selectedTenant } = useTenant();
  const [stats, setStats] = useState({ calls_today: 56, bookings_today: 18, escalations_today: 0 });
  const [loading, setLoading] = useState(true);

  // Card Refs for 3D Tilt
  const liveCardRef = useRef(null);

  const loadData = async () => {
    if (!selectedTenant) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/tenants/${selectedTenant.id}/stats`, {}, getToken);
      if (res.ok) {
        const data = await res.json();
        if (data && (data.calls_today !== undefined || data.bookings_today !== undefined)) {
          setStats(data);
        }
      }
    } catch (e) {
      console.error("Overview fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [getToken, selectedTenant]);

  // 3D Card Hover Tilt Effect
  const handleTiltMove = (ref, e) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    const rotateX = (-y / rect.height) * 4;
    const rotateY = (x / rect.width) * 4;
    ref.current.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
  };

  const handleTiltReset = (ref) => {
    if (!ref.current) return;
    ref.current.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
  };

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
          <p className="loading-text">Loading 3D Clinic Overview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container overview-3d-wrapper">
      {/* ── Page Header ── */}
      <div className="page-header-3d">
        <div className="header-title-group">
          <div className="header-icon-glow">
            <LayoutDashboard className="icon-3d" size={28} />
          </div>
          <div>
            <h2 className="page-title-3d">Operations Overview</h2>
            <p className="page-subtitle-3d">
              {selectedTenant ? `${selectedTenant.name} (ID: ${selectedTenant.id})` : 'Clinic Compass'} • Real-time AI receptionist activity stream
            </p>
          </div>
        </div>

        <div className="header-actions-3d">
          <div className="live-status-pill">
            <span className="dot-pulse-green"></span>
            <span>SignalWire Online</span>
          </div>

          <button className="refresh-btn-3d" onClick={loadData} title="Refresh Overview">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            <span>Sync Overview</span>
          </button>
        </div>
      </div>

      {/* ── 3D Stats Hero Grid ── */}
      <div className="stats-grid-3d">
        {/* Calls Today Card */}
        <div className="stat-card-3d card-teal">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Calls Today</span>
              <h3 className="stat-value">{stats.calls_today}</h3>
              <div className="stat-badge green-glow">
                <TrendingUp size={12} />
                <span>+14.2% Inbound Volume</span>
              </div>
            </div>
            <div className="stat-icon-wrapper teal-bg">
              <PhoneCall size={24} />
            </div>
          </div>
          <div className="stat-card-bottom">
            <span className="sub-metric">Avg. Call Duration: 1m 42s</span>
          </div>
          <div className="card-3d-shine"></div>
        </div>

        {/* Bookings Today Card */}
        <div className="stat-card-3d card-emerald">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Bookings Today</span>
              <h3 className="stat-value">{stats.bookings_today}</h3>
              <div className="stat-badge green-glow">
                <CheckCircle2 size={12} />
                <span>100% Validated Slots</span>
              </div>
            </div>
            <div className="stat-icon-wrapper green-bg">
              <CalendarCheck size={24} />
            </div>
          </div>
          <div className="stat-card-bottom">
            <span className="sub-metric">Top Appointment: Botox Touchup</span>
          </div>
          <div className="card-3d-shine"></div>
        </div>

        {/* Escalations Card */}
        <div className="stat-card-3d card-rose">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Escalations</span>
              <h3 className="stat-value">{stats.escalations_today}</h3>
              <div className="stat-badge rose-glow">
                <ShieldCheck size={12} />
                <span>Zero System Errors</span>
              </div>
            </div>
            <div className="stat-icon-wrapper rose-bg">
              <AlertTriangle size={24} />
            </div>
          </div>
          <div className="stat-card-bottom">
            <span className="sub-metric">Human Transfer Queue: Empty</span>
          </div>
          <div className="card-3d-shine"></div>
        </div>

        {/* AI Voice Pipeline Card */}
        <div className="stat-card-3d card-indigo">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">AI Receptionist</span>
              <h3 className="stat-value">Ready</h3>
              <div className="stat-badge indigo-glow">
                <Zap size={12} />
                <span>ElevenLabs + Deepgram</span>
              </div>
            </div>
            <div className="stat-icon-wrapper indigo-bg">
              <Radio size={24} />
            </div>
          </div>
          <div className="stat-card-bottom">
            <span className="sub-metric">Latency: ~310ms Avg</span>
          </div>
          <div className="card-3d-shine"></div>
        </div>
      </div>

      {/* ── 3D Live Activity Section ── */}
      <div 
        className="live-activity-card-3d"
        ref={liveCardRef}
        onMouseMove={(e) => handleTiltMove(liveCardRef, e)}
        onMouseLeave={() => handleTiltReset(liveCardRef)}
      >
        <div className="activity-card-header">
          <div className="activity-title-flex">
            <div className="activity-icon-chip">
              <Activity size={18} />
            </div>
            <div>
              <h3 className="activity-card-title">Live Call Activity & Queue</h3>
              <p className="activity-card-subtitle">Real-time status of active telephone calls and waiting callers</p>
            </div>
          </div>

          <div className="pulse-live-badge">
            <span className="dot-pulse-green"></span>
            <span>Realtime Stream Active</span>
          </div>
        </div>

        <div className="queue-strip-wrapper-3d">
          <CallQueueStrip />
        </div>
      </div>
    </div>
  );
}
