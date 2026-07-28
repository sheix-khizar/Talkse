import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';
import './ErrorBoundary.css';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an issue:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-fallback">
          <div className="error-card">
            <AlertOctagon size={42} className="error-icon" />
            <h2>Dashboard Component Error</h2>
            <p>An unexpected UI error occurred while rendering the dashboard.</p>
            <button className="btn-retry" onClick={this.handleReset}>
              <RotateCcw size={16} />
              <span>Retry Dashboard</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
