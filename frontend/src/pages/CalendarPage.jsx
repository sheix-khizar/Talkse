import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { fetchAppointments } from '../api/appointments';

export default function CalendarPage() {
  const { getToken } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAppointments(getToken)
      .then(data => {
        setAppointments(data);
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  }, [getToken]);

  if (loading) {
    return (
      <div className="page-container flex-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  // Very rudimentary grouped-by-date logic
  const grouped = appointments.reduce((acc, appt) => {
    const dateKey = new Date(appt.scheduled_start).toLocaleDateString();
    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(appt);
    return acc;
  }, {});

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Calendar</h2>
      </div>
      
      {error && <div className="error-banner">{error}</div>}

      <div className="calendar-grid" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {Object.keys(grouped).length === 0 ? (
          <div className="empty-state">No upcoming appointments.</div>
        ) : (
          Object.keys(grouped).map(dateKey => (
            <div key={dateKey} className="calendar-day">
              <h3 style={{ marginBottom: '1rem', color: 'var(--text-color)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>{dateKey}</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem' }}>
                {grouped[dateKey].map(a => (
                  <div key={a.id} style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{new Date(a.scheduled_start).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{a.caller_name || 'Unknown'}</div>
                    <div style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                      <span className="badge badge-secondary">{a.service_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
