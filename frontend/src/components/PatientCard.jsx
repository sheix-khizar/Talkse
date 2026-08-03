import React, { useState, memo } from 'react';
import { MoreHorizontal } from 'lucide-react';
import './PatientCard.css';

const PatientCard = memo(function PatientCard({ patient, isLoading = false }) {
  const [notes, setNotes] = useState(patient?.notes || '');

  if (isLoading) {
    return (
      <div className="patient-card-container skeleton-container">
        <div className="card-header">
          <div className="skeleton-title" />
        </div>
        <div className="patient-profile">
          <div className="skeleton-avatar" />
          <div className="skeleton-text-group">
            <div className="skeleton-line short" />
            <div className="skeleton-line long" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="patient-card-container">
      {/* Header */}
      <div className="card-header">
        <h3 className="card-title">PATIENT CARD</h3>
        <button className="card-menu-btn" aria-label="Patient options">
          <MoreHorizontal size={18} />
        </button>
      </div>

      {/* Patient Main Profile */}
      {patient ? (
        <>
          <div className="patient-profile">
            {patient.avatar && (
              <img src={patient.avatar} alt={patient.name} className="patient-avatar" />
            )}
            <div className="patient-meta">
              <span className="customer-tag">{patient.customerType || 'Unknown'}</span>
              <h4 className="patient-name">{patient.name || 'Unnamed Caller'}</h4>
            </div>
          </div>

          <div className="patient-details">
            <div className="detail-group">
              <span className="detail-label">Phone</span>
              <span className="detail-value">{patient.phone || '—'}</span>
            </div>
          </div>

          <hr className="card-divider" />

          <div className="previous-appts-section">
            <h4 className="section-title">Previous Appointments</h4>
            {patient.previousAppointments?.length > 0 ? (
              <ul className="appts-list">
                {patient.previousAppointments.map((appt, idx) => (
                  <li key={idx} className="appt-item">{appt}</li>
                ))}
              </ul>
            ) : (
              <p className="empty-state-text">No previous appointments on record.</p>
            )}
          </div>
        </>
      ) : (
        <p className="empty-state-text">No patient record for this call yet.</p>
      )}

      <hr className="card-divider" />

      {/* Call Notes */}
      <div className="call-notes-section">
        <h4 className="section-title">Call Notes</h4>
        <textarea
          className="call-notes-textarea"
          placeholder="Call Notes..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>
    </div>
  );
});

export default PatientCard;
