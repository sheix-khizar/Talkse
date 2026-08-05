import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTenant } from '../context/TenantContext';
import { fetchTenantConfig, updateTenantPlan } from '../api/tenants';
import { 
  Sliders, 
  Cpu, 
  Building, 
  Users, 
  Stethoscope, 
  CheckCircle2, 
  Sparkles, 
  Clock, 
  Globe, 
  AlertCircle, 
  RefreshCw, 
  ShieldCheck,
  Check,
  Zap,
  Volume2
} from 'lucide-react';
import './SettingsPage.css';

// Provider avatar initials generator
const getInitials = (name) => {
  if (!name) return 'DR';
  const parts = name.trim().split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
};

export default function SettingsPage() {
  const { getToken } = useAuth();
  const { selectedTenant } = useTenant();
  
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savingPlan, setSavingPlan] = useState(false);

  // 3D Tilt Effect Refs
  const pipelineCardRef = useRef(null);
  const profileCardRef = useRef(null);

  const loadConfig = async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTenantConfig(selectedTenant.id, getToken);
      setConfig(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, [selectedTenant, getToken]);

  const handlePlanSelect = async (newPlan) => {
    if (!config || config.clinic?.plan === newPlan || savingPlan) return;
    setSavingPlan(true);
    try {
      await updateTenantPlan(selectedTenant.id, newPlan, getToken);
      setConfig({ ...config, clinic: { ...config.clinic, plan: newPlan } });
    } catch (err) {
      alert("Failed to update plan: " + err.message);
    } finally {
      setSavingPlan(false);
    }
  };

  // 3D Perspective Tilt on Mouse Movement
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
          <p className="loading-text">Loading 3D Clinic Configuration...</p>
        </div>
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="page-container">
        <div className="error-banner-3d">
          <AlertCircle size={20} />
          <span>{error || 'Failed to load clinic configuration'}</span>
        </div>
      </div>
    );
  }

  const { clinic, providers, services } = config;
  const currentPlan = clinic.plan || 'free';

  return (
    <div className="page-container settings-3d-wrapper">
      {/* ── Page Header ── */}
      <div className="page-header-3d">
        <div className="header-title-group">
          <div className="header-icon-glow">
            <Sliders className="icon-3d" size={28} />
          </div>
          <div>
            <h2 className="page-title-3d">Clinic & AI Settings</h2>
            <p className="page-subtitle-3d">Manage voice synthesis models, staff members & clinic operating hours</p>
          </div>
        </div>

        <button className="refresh-btn-3d" onClick={loadConfig} title="Sync Settings">
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          <span>Sync Settings</span>
        </button>
      </div>

      {/* ── 1. AI Voice Pipeline Selection ── */}
      <div className="settings-section-3d">
        <div className="section-header-3d">
          <div className="section-icon-chip purple-chip">
            <Cpu size={18} />
          </div>
          <div>
            <h3 className="section-title-3d">AI Voice Synthesis Pipeline</h3>
            <p className="section-desc-3d">Select the live TTS model used for outbound and inbound AI telephone calls.</p>
          </div>
        </div>

        <div 
          className="pipeline-options-grid-3d"
          ref={pipelineCardRef}
          onMouseMove={(e) => handleTiltMove(pipelineCardRef, e)}
          onMouseLeave={() => handleTiltReset(pipelineCardRef)}
        >
          {/* ElevenLabs Premium Option */}
          <div 
            className={`pipeline-card-3d ${currentPlan === 'paid' ? 'active-elevenlabs' : ''}`}
            onClick={() => handlePlanSelect('paid')}
          >
            {currentPlan === 'paid' && (
              <div className="active-badge-pill purple-badge">
                <Check size={12} /> Active Voice Engine
              </div>
            )}
            <div className="pipeline-card-header">
              <div className="pipeline-logo-glow purple-glow">
                <Volume2 size={24} />
              </div>
              <div>
                <h4 className="pipeline-name">ElevenLabs Premium TTS</h4>
                <span className="pipeline-tag">Multilingual v2 • Ultra Realism</span>
              </div>
            </div>

            <p className="pipeline-desc">
              Human-like inflection, expressive vocal tones, and premium studio-quality voice output. Recommended for clinic bookings.
            </p>

            <div className="pipeline-specs">
              <div className="spec-item"><Sparkles size={12} /> High Definition 16kHz PCM</div>
              <div className="spec-item"><ShieldCheck size={12} /> Auto Fallback to Deepgram</div>
            </div>

            <button 
              className={`select-pipeline-btn ${currentPlan === 'paid' ? 'btn-active-purple' : ''}`}
              disabled={savingPlan}
            >
              {savingPlan && currentPlan !== 'paid' ? 'Switching...' : currentPlan === 'paid' ? 'Selected Model' : 'Switch to ElevenLabs'}
            </button>
          </div>

          {/* Deepgram Standard Option */}
          <div 
            className={`pipeline-card-3d ${currentPlan === 'free' ? 'active-deepgram' : ''}`}
            onClick={() => handlePlanSelect('free')}
          >
            {currentPlan === 'free' && (
              <div className="active-badge-pill cyan-badge">
                <Check size={12} /> Active Voice Engine
              </div>
            )}
            <div className="pipeline-card-header">
              <div className="pipeline-logo-glow cyan-glow">
                <Zap size={24} />
              </div>
              <div>
                <h4 className="pipeline-name">Deepgram Aura TTS</h4>
                <span className="pipeline-tag">Standard Baseline • Low Latency</span>
              </div>
            </div>

            <p className="pipeline-desc">
              Fast synthesis optimized for high throughput telephony with responsive latency under 120ms.
            </p>

            <div className="pipeline-specs">
              <div className="spec-item"><Zap size={12} /> Ultra-Fast Response</div>
              <div className="spec-item"><CheckCircle2 size={12} /> Linear 16kHz Audio</div>
            </div>

            <button 
              className={`select-pipeline-btn ${currentPlan === 'free' ? 'btn-active-cyan' : ''}`}
              disabled={savingPlan}
            >
              {savingPlan && currentPlan !== 'free' ? 'Switching...' : currentPlan === 'free' ? 'Selected Model' : 'Switch to Deepgram'}
            </button>
          </div>
        </div>
      </div>

      {/* ── 2. Clinic Profile & Operating Hours ── */}
      <div className="settings-section-3d">
        <div className="section-header-3d">
          <div className="section-icon-chip teal-chip">
            <Building size={18} />
          </div>
          <div>
            <h3 className="section-title-3d">Clinic Profile & Operating Schedule</h3>
            <p className="section-desc-3d">Clinic credentials, region settings and business hours (Read-only)</p>
          </div>
        </div>

        <div 
          className="profile-card-3d"
          ref={profileCardRef}
          onMouseMove={(e) => handleTiltMove(profileCardRef, e)}
          onMouseLeave={() => handleTiltReset(profileCardRef)}
        >
          <div className="profile-top-info">
            <div className="clinic-main-details">
              <h4 className="clinic-title-name">{clinic.name}</h4>
              <div className="clinic-meta-badges">
                <span className="meta-badge"><Building size={12} /> Tenant ID: #{clinic.id}</span>
                <span className="meta-badge"><Globe size={12} /> Timezone: {clinic.timezone || 'America/Chicago'}</span>
              </div>
            </div>
          </div>

          <div className="hours-divider">
            <span className="divider-label"><Clock size={14} /> Weekly Business Hours Schedule</span>
          </div>

          <div className="hours-grid-3d">
            {clinic.hours && Object.entries(clinic.hours).map(([day, times]) => {
              const isOpen = Boolean(times.open);

              return (
                <div key={day} className={`hour-pill-3d ${isOpen ? 'hour-open' : 'hour-closed'}`}>
                  <span className="day-name">{day}</span>
                  <span className="time-range">
                    {isOpen ? `${times.open} - ${times.close}` : 'Closed'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── 3. Providers Directory ── */}
      <div className="settings-section-3d">
        <div className="section-header-3d">
          <div className="section-icon-chip emerald-chip">
            <Users size={18} />
          </div>
          <div>
            <h3 className="section-title-3d">Staff & Providers</h3>
            <p className="section-desc-3d">Practitioners available for patient appointments</p>
          </div>
        </div>

        <div className="providers-grid-3d">
          {providers.map((p) => (
            <div key={p.id} className="provider-card-3d">
              <div className="provider-avatar-3d">
                {getInitials(p.name)}
              </div>
              <div className="provider-info">
                <h4 className="provider-name-text">{p.name}</h4>
                <span className="provider-id-tag">ID: {p.id}</span>
              </div>
              <div className="provider-badge-status">
                <span className="dot-green"></span>
                <span>Available</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 4. Treatments & Services Directory ── */}
      <div className="settings-section-3d">
        <div className="section-header-3d">
          <div className="section-icon-chip indigo-chip">
            <Stethoscope size={18} />
          </div>
          <div>
            <h3 className="section-title-3d">Services & Treatments Directory</h3>
            <p className="section-desc-3d">Offered procedures, duration & medical contraindications</p>
          </div>
        </div>

        <div className="services-grid-3d">
          {services.map((s) => (
            <div key={s.id} className="service-card-3d">
              <div className="service-card-top">
                <h4 className="service-name-text">{s.name}</h4>
                <span className="duration-chip"><Clock size={12} /> {s.duration_minutes} min</span>
              </div>

              <span className="service-id-sub">Service Code: {s.id}</span>

              {s.contraindications && s.contraindications.length > 0 && (
                <div className="contra-section">
                  <span className="contra-label">Contraindications:</span>
                  <div className="contra-pills-flex">
                    {s.contraindications.map((c, i) => (
                      <span key={i} className="contra-badge-3d">{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
