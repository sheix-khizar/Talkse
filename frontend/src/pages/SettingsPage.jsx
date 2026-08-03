import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTenant } from '../context/TenantContext';
import { fetchTenantConfig, updateTenantPlan } from '../api/tenants';
import './SettingsPage.css';

export default function SettingsPage() {
  const { getToken } = useAuth();
  const { selectedTenant } = useTenant();
  
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savingPlan, setSavingPlan] = useState(false);

  useEffect(() => {
    async function loadConfig() {
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
    }
    loadConfig();
  }, [selectedTenant, getToken]);

  const handlePlanChange = async (e) => {
    const newPlan = e.target.value;
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

  if (loading) {
    return (
      <div className="page-container flex-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="page-container">
        <div className="error-banner">{error || 'Failed to load config'}</div>
      </div>
    );
  }

  const { clinic, providers, services } = config;

  return (
    <div className="page-container settings-container">
      <div className="page-header">
        <h2 className="page-title">Settings</h2>
      </div>

      <div className="settings-section">
        <h3>AI Pipeline</h3>
        <p className="section-desc">Select the active voice model pipeline for this clinic.</p>
        <div className="settings-card">
          <label className="settings-label">Active Plan</label>
          <select 
            className="settings-select" 
            value={clinic.plan || 'free'} 
            onChange={handlePlanChange}
            disabled={savingPlan}
          >
            <option value="free">Standard (Deepgram TTS)</option>
            <option value="paid">Premium (ElevenLabs TTS)</option>
          </select>
          {savingPlan && <span style={{ marginLeft: '1rem', color: 'var(--text-muted)' }}>Saving...</span>}
        </div>
      </div>

      <div className="settings-section">
        <h3>Clinic Profile</h3>
        <p className="section-desc">General information and operating hours (Read-only)</p>
        <div className="settings-card profile-card">
          <div className="profile-row">
            <span className="profile-label">Name</span>
            <span className="profile-value">{clinic.name}</span>
          </div>
          <div className="profile-row">
            <span className="profile-label">Timezone</span>
            <span className="profile-value">{clinic.timezone}</span>
          </div>
          <div className="profile-row hours-row">
            <span className="profile-label">Hours</span>
            <div className="hours-list">
              {clinic.hours && Object.entries(clinic.hours).map(([day, times]) => (
                <div key={day} className="hour-item">
                  <span className="hour-day">{day}</span>
                  <span className="hour-time">
                    {times.open ? `${times.open} - ${times.close}` : 'Closed'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h3>Providers</h3>
        <p className="section-desc">Staff members available for appointments (Read-only)</p>
        <div className="settings-grid">
          {providers.map(p => (
            <div key={p.id} className="settings-card item-card">
              <h4>{p.name}</h4>
              <p>ID: {p.id}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="settings-section">
        <h3>Services</h3>
        <p className="section-desc">Treatments and services offered (Read-only)</p>
        <div className="settings-grid">
          {services.map(s => (
            <div key={s.id} className="settings-card item-card">
              <h4>{s.name}</h4>
              <p>Duration: {s.duration_minutes} min</p>
              {s.contraindications && s.contraindications.length > 0 && (
                <div className="contra-tags">
                  {s.contraindications.map((c, i) => (
                    <span key={i} className="badge badge-secondary">{c}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
