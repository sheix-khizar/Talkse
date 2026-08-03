import React, { useState, useEffect, memo } from 'react';
import { MoreHorizontal, Edit3, CheckCircle, Calendar } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { createAppointment } from '../api/bookings';
import './NluBookingPanel.css';

const NluBookingPanel = memo(function NluBookingPanel({ nlu, tenantId = '042' }) {
  const { getToken } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [isBooking, setIsBooking] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState(null);

  const [slots, setSlots] = useState({
    intent: nlu?.intent?.label || '',
    provider: nlu?.provider?.label || '',
    time: nlu?.time?.label || '',
    service: nlu?.service?.label || ''
  });

  // Keep in sync as real NLU data arrives over the WebSocket after mount —
  // the state above only captures the value at first render otherwise.
  useEffect(() => {
    setSlots({
      intent: nlu?.intent?.label || '',
      provider: nlu?.provider?.label || '',
      time: nlu?.time?.label || '',
      service: nlu?.service?.label || ''
    });
  }, [nlu]);

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
      }, getToken);
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

      {!nlu && (
        <p className="empty-state-text">No booking data extracted from this call yet.</p>
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
          <span className="slot-confidence">
            {nlu?.intent?.confidence != null ? `${nlu.intent.confidence}%` : '—'}
          </span>
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
          <span className="slot-confidence">
            {nlu?.provider?.confidence != null ? `${nlu.provider.confidence}%` : '—'}
          </span>
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
          <span className="slot-confidence">
            {nlu?.time?.confidence != null ? `${nlu.time.confidence}%` : '—'}
          </span>
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
          <span className="slot-confidence">
            {nlu?.service?.confidence != null ? `${nlu.service.confidence}%` : '—'}
          </span>
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
