import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Send, Mail, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import './EmailDraftModal.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

/**
 * EmailDraftModal - Human-in-the-loop popup for email drafts
 * Allows users to review, edit, and send email drafts
 */
export function EmailDraftModal({ draft, onClose, onSend, onUpdate }) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const [formData, setFormData] = useState({
    to: '',
    cc: '',
    bcc: '',
    subject: '',
    body: ''
  });

  // Initialize form data from draft
  useEffect(() => {
    if (draft) {
      setFormData({
        to: draft.to || '',
        cc: draft.cc || '',
        bcc: draft.bcc || '',
        subject: draft.subject || '',
        body: draft.body || ''
      });
    }
  }, [draft]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setIsEditing(true);
  };

  const handleUpdate = async () => {
    setIsUpdating(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.put(
        `${API_BASE_URL}/email/draft/${draft.draft_id}`,
        formData,
        {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        }
      );

      if (response.data.status === 'success') {
        setSuccess('Draft updated successfully!');
        setIsEditing(false);
        if (onUpdate) {
          onUpdate(response.data.result);
        }
        setTimeout(() => setSuccess(null), 3000);
      }
    } catch (err) {
      console.error('Failed to update draft:', err);
      
      // Handle error message - could be string or object
      let errorMessage = 'Failed to update draft';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // FastAPI validation errors
          errorMessage = detail.map(e => e.msg).join(', ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      }
      
      setError(errorMessage);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleSend = async () => {
    setIsSending(true);
    setError(null);
    
    try {
      // Update draft first if there are unsaved changes
      if (isEditing) {
        await handleUpdate();
      }

      const token = localStorage.getItem('auth_token');
      
      // Approve the draft
      await axios.post(
        `${API_BASE_URL}/email/send`,
        { draft_id: draft.draft_id },
        {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        }
      );

      // Send the draft
      const response = await axios.post(
        `${API_BASE_URL}/email/send`,
        { draft_id: draft.draft_id },
        {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        }
      );

      if (response.data.status === 'success') {
        setSuccess('Email sent successfully!');
        if (onSend) {
          onSend(draft.draft_id);
        }
        setTimeout(() => {
          onClose();
        }, 1500);
      }
    } catch (err) {
      console.error('Failed to send email:', err);
      
      // Handle error message - could be string or object
      let errorMessage = 'Failed to send email. Please try again.';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // FastAPI validation errors
          errorMessage = detail.map(e => e.msg).join(', ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      }
      
      setError(errorMessage);
    } finally {
      setIsSending(false);
    }
  };

  if (!draft) return null;

  return (
    <div className="email-draft-modal-overlay" onClick={onClose}>
      <div className="email-draft-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="header-title">
            <Mail className="header-icon" />
            <h2>Review Email Draft</h2>
          </div>
          <button className="close-button" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="alert alert-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
        
        {success && (
          <div className="alert alert-success">
            <CheckCircle size={16} />
            <span>{success}</span>
          </div>
        )}

        {/* Form */}
        <div className="modal-body">
          <div className="form-group">
            <label htmlFor="to">To *</label>
            <input
              type="email"
              id="to"
              name="to"
              value={formData.to}
              onChange={handleInputChange}
              placeholder="recipient@example.com"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="cc">CC</label>
            <input
              type="email"
              id="cc"
              name="cc"
              value={formData.cc}
              onChange={handleInputChange}
              placeholder="cc@example.com (optional)"
            />
          </div>

          <div className="form-group">
            <label htmlFor="bcc">BCC</label>
            <input
              type="email"
              id="bcc"
              name="bcc"
              value={formData.bcc}
              onChange={handleInputChange}
              placeholder="bcc@example.com (optional)"
            />
          </div>

          <div className="form-group">
            <label htmlFor="subject">Subject *</label>
            <input
              type="text"
              id="subject"
              name="subject"
              value={formData.subject}
              onChange={handleInputChange}
              placeholder="Email subject"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="body">Message *</label>
            <textarea
              id="body"
              name="body"
              value={formData.body}
              onChange={handleInputChange}
              placeholder="Email body..."
              rows={12}
              required
            />
          </div>

          {/* Draft Metadata */}
          <div className="draft-metadata">
            <div className="metadata-item">
              <span className="metadata-label">Status:</span>
              <span className={`status-badge status-${draft.status}`}>
                {draft.status?.replace('_', ' ').toUpperCase()}
              </span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Created:</span>
              <span>{new Date(draft.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onClose}
            disabled={isSending || isUpdating}
          >
            Close
          </button>

          {isEditing && (
            <button
              className="btn btn-primary"
              onClick={handleUpdate}
              disabled={isSending || isUpdating}
            >
              {isUpdating ? (
                <>
                  <Loader2 className="spinner" size={16} />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
          )}

          <button
            className="btn btn-success"
            onClick={handleSend}
            disabled={isSending || isUpdating || !formData.to || !formData.subject || !formData.body}
          >
            {isSending ? (
              <>
                <Loader2 className="spinner" size={16} />
                Sending...
              </>
            ) : (
              <>
                <Send size={16} />
                Send Email
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default EmailDraftModal;
