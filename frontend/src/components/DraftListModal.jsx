import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Mail, Clock, CheckCircle, XCircle, Eye, Loader2 } from 'lucide-react';
import './DraftListModal.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

/**
 * DraftListModal - Shows all email drafts for current session
 */
export function DraftListModal({ sessionId, onClose, onSelectDraft }) {
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDrafts();
  }, [sessionId]);

  const loadDrafts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(
        `${API_BASE_URL}/email/drafts/${sessionId}`,
        {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        }
      );

      if (response.data.status === 'success') {
        setDrafts(response.data.result.drafts || []);
      }
    } catch (err) {
      console.error('Failed to load drafts:', err);
      setError(err.response?.data?.detail || 'Failed to load drafts');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending_approval':
        return <Clock size={16} />;
      case 'approved':
        return <CheckCircle size={16} />;
      case 'sent':
        return <CheckCircle size={16} />;
      case 'rejected':
        return <XCircle size={16} />;
      default:
        return <Mail size={16} />;
    }
  };

  const handleDraftClick = async (draftId) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(
        `${API_BASE_URL}/email/draft/${draftId}`,
        {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
          params: { session_id: sessionId }
        }
      );

      if (onSelectDraft) {
        onSelectDraft(response.data);
      }
      onClose();
    } catch (err) {
      console.error('Failed to load draft details:', err);
      setError(err.response?.data?.detail || 'Failed to load draft details');
    }
  };

  return (
    <div className="draft-list-modal-overlay" onClick={onClose}>
      <div className="draft-list-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="header-title">
            <Mail className="header-icon" />
            <h2>Email Drafts</h2>
          </div>
          <button className="close-button" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {loading ? (
            <div className="loading-state">
              <Loader2 className="spinner" size={32} />
              <p>Loading drafts...</p>
            </div>
          ) : error ? (
            <div className="error-state">
              <XCircle size={32} />
              <p>{error}</p>
              <button className="btn btn-primary" onClick={loadDrafts}>
                Retry
              </button>
            </div>
          ) : drafts.length === 0 ? (
            <div className="empty-state">
              <Mail size={48} />
              <h3>No drafts yet</h3>
              <p>Email drafts you create will appear here</p>
            </div>
          ) : (
            <div className="drafts-list">
              {drafts.map((draft) => (
                <div
                  key={draft.draft_id}
                  className="draft-card"
                  onClick={() => handleDraftClick(draft.draft_id)}
                >
                  <div className="draft-header">
                    <div className="draft-status">
                      {getStatusIcon(draft.status)}
                      <span className={`status-badge status-${draft.status}`}>
                        {draft.status.replace('_', ' ')}
                      </span>
                    </div>
                    <Eye size={16} className="view-icon" />
                  </div>

                  <div className="draft-content">
                    <div className="draft-to">
                      <strong>To:</strong> {draft.to}
                    </div>
                    <div className="draft-subject">
                      <strong>Subject:</strong> {draft.subject || '(No Subject)'}
                    </div>
                    <div className="draft-date">
                      <Clock size={14} />
                      <span>{new Date(draft.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <div className="draft-count">
            {drafts.length} {drafts.length === 1 ? 'draft' : 'drafts'}
          </div>
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default DraftListModal;
