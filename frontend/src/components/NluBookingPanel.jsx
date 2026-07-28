import React, { useState, memo } from 'react';
import { MoreHorizontal, Edit3, CheckCircle, Calendar } from 'lucide-react';
import { createAppointment } from '../api/bookings';
import './NluBookingPanel.css';

const NluBookingPanel = memo(function NluBookingPanel({ nlu, tenantId = '042' }) {
  const [isEditing, setIsEditing] = useState(false);
  const [isBooking, setIsBooking] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState(null);

  const [slots, setSlots] = useState({
    intent: nlu?.intent?.label || 'Schedule Appointment',
    provider: nlu?.provider?.label || 'Dr. Smith',
    time: nlu?.time?.label || '16:00, Tuesday',
    service: nlu?.service?.label || 'Botox Touch-up'
  });

  const handleSlotChange = (key, value) => {
    setSlots((prev) => ({ ...prev, [key]: value }));
  };

  const handleConfirmBooking = async () => {
    setIsBooking(true);
    setBookingSuccess(null);
    try {
      const res = await createAppointment(tenantId, {
        intent: slots.intent,
        provider: slots.provider,
        time: slots.time,
        service: slots.service
      });
      setBookingSuccess(res.message || 'Appointment confirmed!');
      setIsEditing(false);
    } catch (err) {
      console.error("Booking error:", err);
    } finally {
      setIsBooking(false);
    }
  };

  return (
    <div className="nlu-panel-container">
      <div className="nlu-header">
        <div className="nlu-header-left">
          <h3 className="nlu-title">NLU & BOOKING ACTION</h3>
        </div>
        <div className="nlu-header-actions">
          <button
            className={`nlu-edit-btn ${isEditing ? 'active' : ''}`}
            onClick={() => setIsEditing(!isEditing)}
          >
            <Edit3 size={14} />
            <span>{isEditing ? 'Cancel Edit' : 'Edit Slots'}</span>
          </button>
          <button className="nlu-menu-btn" aria-label="NLU options">
            <MoreHorizontal size={18} />
          </button>
        </div>
      </div>

      {bookingSuccess && (
        <div className="booking-success-toast">
          <CheckCircle size={16} />
          <span>{bookingSuccess}</span>
        </div>
      )}

      {/* 2x2 Slot Grid */}
      <div className="nlu-grid">
        <div className="nlu-slot-card">
          <div className="slot-info">
            <strong className="slot-label">Intent:</strong>
            {isEditing ? (
              <input
                type="text"
                className="slot-inline-input"
                value={slots.intent}
                onChange={(e) => handleSlotChange('intent', e.target.value)}
              />
            ) : (
              <span className="slot-value">{slots.intent}</span>
            )}
          </div>
          <span className="slot-confidence">100%</span>
        </div>

        <div className="nlu-slot-card">
          <div className="slot-info">
            <strong className="slot-label">Provider:</strong>
            {isEditing ? (
              <input
                type="text"
                className="slot-inline-input"
                value={slots.provider}
                onChange={(e) => handleSlotChange('provider', e.target.value)}
              />
            ) : (
              <span className="slot-value">{slots.provider}</span>
            )}
          </div>
          <span className="slot-confidence">100%</span>
        </div>

        <div className="nlu-slot-card">
          <div className="slot-info">
            <strong className="slot-label">Time:</strong>
            {isEditing ? (
              <input
                type="text"
                className="slot-inline-input"
                value={slots.time}
                onChange={(e) => handleSlotChange('time', e.target.value)}
              />
            ) : (
              <span className="slot-value">{slots.time}</span>
            )}
          </div>
          <span className="slot-confidence">100%</span>
        </div>

        <div className="nlu-slot-card">
          <div className="slot-info">
            <strong className="slot-label">Service:</strong>
            {isEditing ? (
              <input
                type="text"
                className="slot-inline-input"
                value={slots.service}
                onChange={(e) => handleSlotChange('service', e.target.value)}
              />
            ) : (
              <span className="slot-value">{slots.service}</span>
            )}
          </div>
          <span className="slot-confidence">100%</span>
        </div>
      </div>

      {/* Booking Action Footer */}
      <div className="nlu-booking-footer">
        <button
          className="btn-confirm-booking"
          onClick={handleConfirmBooking}
          disabled={isBooking}
        >
          <Calendar size={16} />
          <span>{isBooking ? 'Processing Booking...' : 'Confirm and Book Appointment'}</span>
        </button>
      </div>
    </div>
  );
});

export default NluBookingPanel;
