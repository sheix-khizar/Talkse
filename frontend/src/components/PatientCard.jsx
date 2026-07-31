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
      <div className="patient-profile">
        <img
          src={patient?.avatar || "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80"}
          alt={patient?.name || 'Patient Avatar'}
          className="patient-avatar"
        />
        <div className="patient-meta">
          <span className="customer-tag">{patient?.customerType || 'Recurring Customer'}</span>
          <h4 className="patient-name">{patient?.name || 'Sarah Jenkins'}</h4>
        </div>
      </div>

      {/* Contact Details */}
      <div className="patient-details">
        <div className="detail-group">
          <span className="detail-label">Phone</span>
          <span className="detail-value">{patient?.phone || '555-123-4567'}</span>
        </div>
        <div className="detail-group">
          <span className="detail-label">Customer type:</span>
          <span className="detail-value-inline">{patient?.category || 'Lunnoeading'}</span>
        </div>
      </div>

      <hr className="card-divider" />

      {/* Previous Appointments */}
      <div className="previous-appts-section">
        <h4 className="section-title">Previous Appointments</h4>
        <ul className="appts-list">
          {(patient?.previousAppointments || [
            "Last Month - Botox",
            "Last Month - Dr. Smith",
            "Last Month - Botox Touch-up"
          ]).map((appt, idx) => (
            <li key={idx} className="appt-item">
              {appt}
            </li>
          ))}
        </ul>
      </div>

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
