import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTenant } from '../context/TenantContext';
import { apiFetch } from '../api/client';
import CallQueueStrip from '../components/CallQueueStrip';
import './DashboardPage.css';

export default function OverviewPage() {
  const { getToken } = useAuth();
  const { selectedTenant } = useTenant();
  const [stats, setStats] = useState({ calls_today: 0, bookings_today: 0, escalations_today: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!selectedTenant) return;
      setLoading(true);
      try {
        const res = await apiFetch(`/api/v1/tenants/${selectedTenant.id}/stats`, {}, getToken);
        if (res.ok) {
          setStats(await res.json());
        }
      } catch (e) {
        console.error("Overview fetch error:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [getToken, selectedTenant]);

  if (loading) {
    return (
      <div className="page-container flex-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Overview</h2>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-title">Calls Today</div>
          <div className="stat-value">{stats.calls_today}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">Bookings Today</div>
          <div className="stat-value success">{stats.bookings_today}</div>
        </div>
        <div className="stat-card">
          <div className="stat-title">Escalations</div>
          <div className="stat-value error">{stats.escalations_today}</div>
        </div>
      </div>

      <div style={{ marginTop: '2rem' }}>
        <h3>Live Activity</h3>
        <CallQueueStrip />
      </div>
    </div>
  );
}
