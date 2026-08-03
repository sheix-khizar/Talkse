import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { fetchAppointments } from '../api/appointments';
import './AppointmentsPage.css';

export default function AppointmentsPage() {
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
      .catch((e) => {
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

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Appointments</h2>
      </div>
      
      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <div className="table-card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Patient</th>
              <th>Service</th>
              <th>Provider</th>
              <th>Date & Time</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {appointments.length === 0 ? (
              <tr>
                <td colSpan="5" className="empty-state">No appointments found.</td>
              </tr>
            ) : (
              appointments.map((a) => (
                <tr key={a.id}>
                  <td className="font-medium">{a.caller_name || 'Unknown'}</td>
                  <td><span className="badge badge-secondary">{a.service_id}</span></td>
                  <td>{a.provider_id}</td>
                  <td>{new Date(a.scheduled_start).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'})}</td>
                  <td>
                    <span className={`status-dot ${a.status === 'confirmed' ? 'status-green' : 'status-gray'}`} />
                    <span className="capitalize">{a.status}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
