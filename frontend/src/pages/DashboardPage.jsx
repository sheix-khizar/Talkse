import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { useTenant } from '../context/TenantContext';
import { apiFetch } from '../api/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './DashboardPage.css';

// Mock data for the chart since the backend doesn't aggregate historical days yet
const mockChartData = [
  { name: 'Mon', calls: 4 },
  { name: 'Tue', calls: 7 },
  { name: 'Wed', calls: 5 },
  { name: 'Thu', calls: 12 },
  { name: 'Fri', calls: 8 },
  { name: 'Sat', calls: 15 },
  { name: 'Sun', calls: 10 },
];

export default function DashboardPage() {
  const { getToken } = useAuth();
  const { selectedTenant } = useTenant();
  const [stats, setStats] = useState({ calls_today: 0, bookings_today: 0, escalations_today: 0 });
  const [ttsUsage, setTtsUsage] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!selectedTenant) return;
      setLoading(true);
      try {
        const [statsRes, ttsRes] = await Promise.all([
          apiFetch(`/api/v1/tenants/${selectedTenant.id}/stats`, {}, getToken),
          apiFetch(`/api/v1/tenants/${selectedTenant.id}/tts-usage`, {}, getToken)
        ]);
        
        if (statsRes.ok) setStats(await statsRes.json());
        if (ttsRes.ok) setTtsUsage(await ttsRes.json());
      } catch (e) {
        console.error("Dashboard fetch error:", e);
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
        <h2 className="page-title">Dashboard</h2>
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

      <div className="dashboard-row">
        <div className="chart-card">
          <h3>Call Volume (Last 7 Days)</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockChartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dx={-10} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  cursor={{ stroke: '#cbd5e1', strokeWidth: 1, strokeDasharray: '4 4' }}
                />
                <Line type="monotone" dataKey="calls" stroke="var(--accent-color)" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="tts-usage-card">
          <h3>AI Usage</h3>
          <div className="usage-list">
            {ttsUsage.length === 0 ? (
              <div className="text-muted">No usage recorded yet.</div>
            ) : (
              ttsUsage.map((usage, i) => (
                <div key={i} className="usage-item">
                  <div className="usage-provider">{usage.provider}</div>
                  <div className="usage-stats">
                    <span>{usage.calls} calls</span>
                    <span className="dot">•</span>
                    <span>{usage.total_chars.toLocaleString()} chars</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
