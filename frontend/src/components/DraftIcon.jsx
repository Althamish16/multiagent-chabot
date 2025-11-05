import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Mail } from 'lucide-react';
import './DraftIcon.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

/**
 * DraftIcon - Floating icon showing draft count
 * Displays a badge with pending draft count
 */
export function DraftIcon({ sessionId, onClick, isAuthenticated }) {
  const [draftCount, setDraftCount] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (sessionId && isAuthenticated) {
      loadDraftCount();
      
      // Poll for draft count every 10 seconds
      const interval = setInterval(loadDraftCount, 10000);
      return () => clearInterval(interval);
    }
  }, [sessionId, isAuthenticated]);

  const loadDraftCount = async () => {
    if (!sessionId || !isAuthenticated) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(
        `${API_BASE_URL}/email/drafts/${sessionId}`,
        {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        }
      );

      if (response.data.status === 'success') {
        const drafts = response.data.result.drafts || [];
        // Count only pending and approved drafts (not sent)
        const pendingCount = drafts.filter(
          d => d.status === 'pending_approval' || d.status === 'approved'
        ).length;
        setDraftCount(pendingCount);
      }
    } catch (err) {
      console.error('Failed to load draft count:', err);
    } finally {
      setLoading(false);
    }
  };

  // Manually refresh count (called after creating/sending draft)
  useEffect(() => {
    // Expose refresh function globally for other components
    window.refreshDraftCount = loadDraftCount;
    return () => {
      delete window.refreshDraftCount;
    };
  }, [sessionId, isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <button
      className={`draft-icon-button ${draftCount > 0 ? 'has-drafts' : ''}`}
      onClick={onClick}
      aria-label={`Email drafts (${draftCount})`}
      title={`${draftCount} email draft${draftCount !== 1 ? 's' : ''}`}
    >
      <Mail size={24} />
      {draftCount > 0 && (
        <span className="draft-badge">{draftCount > 99 ? '99+' : draftCount}</span>
      )}
      {loading && <span className="loading-indicator" />}
    </button>
  );
}

export default DraftIcon;
