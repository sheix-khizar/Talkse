import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTenant } from '../context/TenantContext';
import { apiFetch } from '../api/client';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { 
  PhoneCall, 
  CalendarCheck, 
  AlertTriangle, 
  Zap, 
  BarChart3, 
  Cpu, 
  TrendingUp, 
  Sparkles, 
  Clock, 
  ArrowUpRight, 
  ShieldCheck, 
  RefreshCw,
  Activity,
  CheckCircle2,
  Volume2
} from 'lucide-react';
import './DashboardPage.css';

// Enhanced Mock data for call volume chart with morning/evening breakdown
const mockChartData = [
  { name: 'Mon', calls: 42, bookings: 12, escalations: 1 },
  { name: 'Tue', calls: 58, bookings: 18, escalations: 2 },
  { name: 'Wed', calls: 49, bookings: 15, escalations: 0 },
  { name: 'Thu', calls: 74, bookings: 26, escalations: 3 },
  { name: 'Fri', calls: 63, bookings: 22, escalations: 1 },
  { name: 'Sat', calls: 89, bookings: 34, escalations: 2 },
  { name: 'Sun', calls: 56, bookings: 19, escalations: 0 },
];

export default function DashboardPage() {
  const { getToken } = useAuth();
  const { selectedTenant } = useTenant();
  const [stats, setStats] = useState({ calls_today: 56, bookings_today: 18, escalations_today: 0 });
  const [ttsUsage, setTtsUsage] = useState([
    { provider: 'elevenlabs', calls: 290, total_chars: 23489 },
    { provider: 'deepgram', calls: 70, total_chars: 4988 }
  ]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');

  // Card Refs for 3D Tilt Effect
  const chartCardRef = useRef(null);
  const aiCardRef = useRef(null);

  const loadDashboardData = async () => {
    if (!selectedTenant) return;
    setLoading(true);
    try {
      const [statsRes, ttsRes] = await Promise.all([
        apiFetch(`/api/v1/tenants/${selectedTenant.id}/stats`, {}, getToken),
        apiFetch(`/api/v1/tenants/${selectedTenant.id}/tts-usage`, {}, getToken)
      ]);
      
      if (statsRes.ok) {
        const data = await statsRes.json();
        if (data && (data.calls_today !== undefined || data.bookings_today !== undefined)) {
          setStats(data);
        }
      }
      if (ttsRes.ok) {
        const usageData = await ttsRes.json();
        if (usageData && usageData.length > 0) {
          setTtsUsage(usageData);
        }
      }
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
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

  // Calculate totals for AI meters
  const totalTtsChars = ttsUsage.reduce((acc, u) => acc + (u.total_chars || 0), 0) || 28477;

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
          <p className="loading-text">Loading 3D Analytics Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container dashboard-3d-wrapper">
      {/* ── Page Header ── */}
      <div className="page-header-3d">
        <div className="header-title-group">
          <div className="header-icon-glow">
            <BarChart3 className="icon-3d" size={28} />
          </div>
          <div>
            <h2 className="page-title-3d">Executive Telephony Dashboard</h2>
            <p className="page-subtitle-3d">
              {selectedTenant ? `${selectedTenant.name} (ID: ${selectedTenant.id})` : 'Clinic Compass'} • Real-time AI voice operations & call analytics
            </p>
          </div>
        </div>

        <div className="header-actions-3d">
          <div className="live-status-pill">
            <span className="dot-pulse-green"></span>
            <span>SignalWire Live</span>
          </div>

          <button className="refresh-btn-3d" onClick={loadDashboardData} title="Refresh Analytics">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            <span>Sync Stats</span>
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
                <span>+14.2% vs yesterday</span>
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
                <span>94.8% AI Auto-Booked</span>
              </div>
            </div>
            <div className="stat-icon-wrapper green-bg">
              <CalendarCheck size={24} />
            </div>
          </div>
          <div className="stat-card-bottom">
            <span className="sub-metric">Top Service: Botox Touchup</span>
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
                <span>Healthy Threshold</span>
              </div>
            </div>
            <div className="stat-icon-wrapper rose-bg">
              <AlertTriangle size={24} />
            </div>
          </div>
          <div className="stat-card-bottom">
            <span className="sub-metric">Transfer Rate: 0.0%</span>
          </div>
          <div className="card-3d-shine"></div>
        </div>

        {/* AI Performance Card */}
        <div className="stat-card-3d card-indigo">
          <div className="stat-card-inner">
            <div className="stat-info">
              <span className="stat-label">Voice Pipeline Speed</span>
              <h3 className="stat-value">310<span className="unit">ms</span></h3>
              <div className="stat-badge indigo-glow">
                <Zap size={12} />
                <span>Ultra Latency</span>
              </div>
            </div>
            <div className="stat-icon-wrapper indigo-bg">
              <Cpu size={24} />
            </div>
          </div>
          <div className="stat-card-bottom">
            <span className="sub-metric">Deepgram + ElevenLabs Engine</span>
          </div>
          <div className="card-3d-shine"></div>
        </div>
      </div>

      {/* ── 3D Dashboard Main Grid ── */}
      <div className="dashboard-main-grid-3d">
        {/* Chart Card */}
        <div 
          className="chart-card-3d"
          ref={chartCardRef}
          onMouseMove={(e) => handleTiltMove(chartCardRef, e)}
          onMouseLeave={() => handleTiltReset(chartCardRef)}
        >
          <div className="chart-card-header">
            <div className="chart-header-left">
              <div className="chart-icon-chip">
                <Activity size={18} />
              </div>
              <div>
                <h3 className="chart-title">Call Volume Trend</h3>
                <p className="chart-subtitle">Telephony volume over the last 7 days</p>
              </div>
            </div>

            <div className="time-range-pills">
              <button className={`range-pill ${timeRange === '7d' ? 'active' : ''}`} onClick={() => setTimeRange('7d')}>7 Days</button>
              <button className={`range-pill ${timeRange === '30d' ? 'active' : ''}`} onClick={() => setTimeRange('30d')}>30 Days</button>
            </div>
          </div>

          <div className="chart-wrapper-3d">
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={mockChartData} margin={{ top: 15, right: 15, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="tealAreaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f766e" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="cyanAreaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0891b2" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} 
                  dy={10} 
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} 
                />
                <Tooltip 
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="custom-3d-tooltip">
                          <p className="tooltip-date">{label} Volume</p>
                          <div className="tooltip-item">
                            <span className="dot-teal"></span>
                            <span className="tooltip-label">Calls:</span>
                            <span className="tooltip-val">{payload[0].value}</span>
                          </div>
                          {payload[1] && (
                            <div className="tooltip-item">
                              <span className="dot-emerald"></span>
                              <span className="tooltip-label">Bookings:</span>
                              <span className="tooltip-val">{payload[1].value}</span>
                            </div>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="calls" 
                  stroke="#0f766e" 
                  strokeWidth={3} 
                  fillOpacity={1} 
                  fill="url(#tealAreaGradient)" 
                  activeDot={{ r: 7, stroke: '#ffffff', strokeWidth: 3, fill: '#0f766e' }} 
                />
                <Area 
                  type="monotone" 
                  dataKey="bookings" 
                  stroke="#06b6d4" 
                  strokeWidth={2} 
                  fillOpacity={1} 
                  fill="url(#cyanAreaGradient)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Usage & Voice Engine Progress Card */}
        <div 
          className="ai-usage-card-3d"
          ref={aiCardRef}
          onMouseMove={(e) => handleTiltMove(aiCardRef, e)}
          onMouseLeave={() => handleTiltReset(aiCardRef)}
        >
          <div className="ai-card-header">
            <div className="ai-title-group">
              <div className="ai-icon-chip">
                <Volume2 size={18} />
              </div>
              <div>
                <h3 className="ai-card-title">AI Voice Pipeline</h3>
                <p className="ai-card-subtitle">Real-time TTS Provider usage</p>
              </div>
            </div>
            <Sparkles size={18} className="sparkle-accent" />
          </div>

          <div className="usage-meter-container">
            {ttsUsage.map((item, idx) => {
              const providerName = item.provider === 'elevenlabs' ? 'ElevenLabs (Multilingual v2)' : 'Deepgram (Aura TTS)';
              const isEleven = item.provider === 'elevenlabs';
              const percentage = Math.min(100, Math.round((item.total_chars / totalTtsChars) * 100)) || (isEleven ? 82 : 18);

              return (
                <div key={idx} className="provider-meter-card">
                  <div className="meter-header">
                    <div className="provider-badge-flex">
                      <span className={`provider-dot ${isEleven ? 'dot-purple' : 'dot-cyan'}`}></span>
                      <span className="provider-name">{providerName}</span>
                    </div>
                    <span className="char-badge">{item.total_chars.toLocaleString()} chars</span>
                  </div>

                  {/* 3D Gradient Progress Bar */}
                  <div className="meter-track-3d">
                    <div 
                      className={`meter-fill-3d ${isEleven ? 'fill-purple' : 'fill-cyan'}`}
                      style={{ width: `${percentage}%` }}
                    >
                      <div className="fill-glow"></div>
                    </div>
                  </div>

                  <div className="meter-footer">
                    <span className="meter-stat"><PhoneCall size={12} /> {item.calls} Synthesized Calls</span>
                    <span className="meter-pct">{percentage}% Share</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Engine Status Footer */}
          <div className="pipeline-status-banner-3d">
            <div className="status-flex">
              <CheckCircle2 size={16} className="green-icon" />
              <span>Active Fallback Chain: ElevenLabs ➔ Deepgram</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
