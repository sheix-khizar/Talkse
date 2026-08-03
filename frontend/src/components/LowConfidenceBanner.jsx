import React from 'react';
import { AlertTriangle } from 'lucide-react';
import './LowConfidenceBanner.css';

export default function LowConfidenceBanner({ confidenceScore = 65, onReviewClick }) {
  if (confidenceScore >= 70) return null;

  return (
    <div className="low-confidence-banner">
      <div className="banner-content">
        <AlertTriangle size={18} className="alert-icon" />
        <span>
          <strong>Low NLU Confidence ({confidenceScore}%):</strong> Please verify extracted slots before confirming booking.
        </span>
      </div>
      {onReviewClick && (
        <button className="review-btn" onClick={onReviewClick}>
          Edit Slots
        </button>
      )}
    </div>
  );
}
