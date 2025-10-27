import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './components/AuthProvider_new';
import { EmailDraftModal } from './components/EmailDraftModal';
import { DraftListModal } from './components/DraftListModal';
import { DraftIcon } from './components/DraftIcon';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

function App() {
  const { isAuthenticated, user, login, logout, loading: authLoading, refreshProfile } = useAuth();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [attachedFile, setAttachedFile] = useState(null);
  const [chatSessions, setChatSessions] = useState([]);
  const [showSidebar, setShowSidebar] = useState(true);
  const [profileImageError, setProfileImageError] = useState(false);
  
  // Email draft states
  const [currentDraft, setCurrentDraft] = useState(null);
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [showDraftList, setShowDraftList] = useState(false);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Initialize session ID
  useEffect(() => {
    const storedSessionId = localStorage.getItem('session_id');
    if (storedSessionId) {
      setSessionId(storedSessionId);
    } else {
      const newSessionId = `session-${Date.now()}`;
      localStorage.setItem('session_id', newSessionId);
      setSessionId(newSessionId);
    }
    
    // Load saved sessions list
    const savedSessions = JSON.parse(localStorage.getItem('chat_sessions') || '[]');
    setChatSessions(savedSessions);
  }, []);

  // Load chat history when session changes
  useEffect(() => {
    if (sessionId && isAuthenticated) {
      loadChatHistory(sessionId);
    } else if (!isAuthenticated) {
      // Show welcome message for non-authenticated users
      setMessages([{
        id: 'welcome',
        message: 'Welcome! Please sign in with Google to access your chat history and all features.',
        sender: 'agent',
        agent_type: 'system',
        timestamp: new Date().toISOString()
      }]);
    }
  }, [sessionId, isAuthenticated]);


  const loadChatHistory = useCallback(async (sessionId) => {
    try {
      console.log('📥 Loading chat history for session:', sessionId);
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(`${API_BASE_URL}/chat/${sessionId}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        console.log('✅ Loaded messages:', response.data.length);
        setMessages(response.data);
      } else {
        console.log('📭 No messages in history');
        setMessages([]);
      }
    } catch (error) {
      console.error('❌ Failed to load chat history:', error);
      setMessages([]);
    }
  }, []);

  const handleImageError = async () => {
    setProfileImageError(true);
    
    // Try to refresh profile to get updated image
    try {
      await refreshProfile();
      setProfileImageError(false); // Reset error if refresh succeeds
    } catch (err) {
      console.error('Failed to refresh profile after image error:', err);
    }
  };

  // Reset image error when user changes
  useEffect(() => {
    setProfileImageError(false);
  }, [user]);

  // Save session to list
  const saveSessionToList = useCallback((sessionId, firstMessage = '') => {
    const sessions = JSON.parse(localStorage.getItem('chat_sessions') || '[]');
    const existingIndex = sessions.findIndex(s => s.id === sessionId);
    
    if (existingIndex >= 0) {
      sessions[existingIndex].lastActivity = new Date().toISOString();
      sessions[existingIndex].preview = firstMessage.substring(0, 50);
    } else {
      sessions.unshift({
        id: sessionId,
        title: firstMessage.substring(0, 30) || 'New Chat',
        preview: firstMessage.substring(0, 50),
        created: new Date().toISOString(),
        lastActivity: new Date().toISOString()
      });
    }
    
    localStorage.setItem('chat_sessions', JSON.stringify(sessions.slice(0, 20)));
    setChatSessions(sessions.slice(0, 20));
  }, []);

  // Create new chat session
  const createNewChat = useCallback(() => {
    const newSessionId = `session-${Date.now()}`;
    localStorage.setItem('session_id', newSessionId);
    setSessionId(newSessionId);
    setMessages([]);
    setInputMessage('');
    setAttachedFile(null);
  }, []);

  // Switch to different session
  const switchSession = useCallback((newSessionId) => {
    localStorage.setItem('session_id', newSessionId);
    setSessionId(newSessionId);
    setMessages([]);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Draft management functions
  const loadAndShowDraft = async (draftId) => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.get(
        `${API_BASE_URL}/email/draft/${draftId}`,
        {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
          params: { session_id: sessionId }
        }
      );

      setCurrentDraft(response.data);
      setShowDraftModal(true);
    } catch (err) {
      console.error('Failed to load draft:', err);
    }
  };

  const handleDraftUpdate = (updatedDraft) => {
    setCurrentDraft(updatedDraft);
  };

  const handleDraftSend = (draftId) => {
    console.log('Email sent:', draftId);
    setShowDraftModal(false);
    setCurrentDraft(null);
    
    // Refresh draft count
    if (window.refreshDraftCount) {
      window.refreshDraftCount();
    }
  };

  const handleCloseDraftModal = () => {
    setShowDraftModal(false);
    // Don't clear currentDraft immediately - user might want to edit via chat
  };

  const handleOpenDraftList = () => {
    setShowDraftList(true);
  };

  const handleSelectDraftFromList = (draft) => {
    setCurrentDraft(draft);
    setShowDraftModal(true);
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setAttachedFile(file);
    }
  };

  const removeFile = () => {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };


  const sendMessage = async () => {
    if (!inputMessage.trim() && !attachedFile) return;

    const messageText = inputMessage.trim();
    
    const userMessage = {
      id: `user-${Date.now()}`,
      message: messageText,
      sender: 'user',
      timestamp: new Date().toISOString()
    };

    console.log('📤 Sending user message:', userMessage);

    // Add user message to UI immediately
    setMessages(prev => {
      const updated = [...prev, userMessage];
      console.log('💬 Messages after user message:', updated.length);
      return updated;
    });
    
    // Save session to list with first message
    if (messages.length === 0 || (messages.length === 1 && messages[0].id === 'welcome')) {
      saveSessionToList(sessionId, messageText);
    }
    
    setInputMessage('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('auth_token');
      const endpoint = isAuthenticated ? '/enhanced-chat' : '/chat';
      let response;

      if (attachedFile) {
        const formData = new FormData();
        formData.append('file', attachedFile);
        formData.append('message', messageText);
        formData.append('session_id', sessionId);

        response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
          headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            'Content-Type': 'multipart/form-data'
          }
        });

        setAttachedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        response = await axios.post(`${API_BASE_URL}${endpoint}`, {
          message: messageText,
          session_id: sessionId
        }, {
          headers: {
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            'Content-Type': 'application/json'
          }
        });
      }

      console.log('📥 Received response:', response.data);

      const agentMessage = {
        id: `agent-${Date.now()}`,
        message: response.data.response || 'No response',
        html_response: response.data.html_response,
        sender: 'agent',
        agent_type: response.data.agent_used || 'general',
        timestamp: response.data.timestamp || new Date().toISOString(),
        agents_involved: response.data.agents_involved || []
      };

      console.log('🤖 Adding agent message:', agentMessage);

      // Add agent response to UI
      setMessages(prev => {
        const updated = [...prev, agentMessage];
        console.log('💬 Messages after agent response:', updated.length);
        return updated;
      });

      // Check if email draft was created
      if (response.data.draft_created) {
        console.log('📧 Draft created:', response.data.draft_created);
        // Load full draft details and show modal
        loadAndShowDraft(response.data.draft_created.draft_id);
        
        // Refresh draft count
        if (window.refreshDraftCount) {
          window.refreshDraftCount();
        }
      }

    } catch (error) {
      console.error('❌ Error sending message:', error);
      const errorMessage = {
        id: `error-${Date.now()}`,
        message: `Sorry, there was an error: ${error.message}`,
        sender: 'agent',
        timestamp: new Date().toISOString(),
        agent_type: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getAgentIcon = (agentType) => {
    const icons = {
      'email_agent': '📧',
      'calendar_agent': '📅',
      'notes_agent': '📝',
      'file_summarizer_agent': '📄',
      'dynamic_langgraph_orchestrator': '🤖',
      'general': '💬',
      'error': '⚠️'
    };
    return icons[agentType] || '🤖';
  };

  const getAgentName = (agentType) => {
    const names = {
      'email_agent': 'Email Agent',
      'calendar_agent': 'Calendar Agent',
      'notes_agent': 'Notes Agent',
      'file_summarizer_agent': 'File Summarizer',
      'dynamic_langgraph_orchestrator': 'AI Orchestrator',
      'general': 'AI Assistant',
      'error': 'Error'
    };
    return names[agentType] || 'AI Assistant';
  };

  if (authLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }


  return (
    <div className="app-container">
      {/* Sidebar for chat history */}
      <aside className={`sidebar ${showSidebar ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div className="sidebar-header">
          <h2>💬 Chats</h2>
          <button onClick={createNewChat} className="btn-new-chat" title="New Chat">
            ➕
          </button>
        </div>
        
        <div className="sessions-list">
          {chatSessions.map(session => (
            <div
              key={session.id}
              className={`session-item ${session.id === sessionId ? 'active' : ''}`}
              onClick={() => switchSession(session.id)}
            >
              <div className="session-title">{session.title || 'New Chat'}</div>
              <div className="session-preview">{session.preview || 'No messages yet'}</div>
              <div className="session-time">
                {new Date(session.lastActivity).toLocaleDateString()}
              </div>
            </div>
          ))}
          
          {chatSessions.length === 0 && (
            <div className="no-sessions">
              <p>No chat history yet</p>
              <p className="text-muted">Start a new conversation!</p>
            </div>
          )}
        </div>
      </aside>

      {/* Main chat area */}
      <div className="main-content">
        <header className="app-header">
          <button 
            className="sidebar-toggle" 
            onClick={() => setShowSidebar(!showSidebar)}
            title={showSidebar ? 'Hide sidebar' : 'Show sidebar'}
          >
            {showSidebar ? '◀' : '▶'}
          </button>
          
          <div className="header-center">
            <h1 className="app-title">
              <span className="title-icon">🤖</span>
              AI Multi-Agent Assistant
            </h1>
          </div>
          
          <div className="header-right">
            {isAuthenticated ? (
              <div className="user-section">
                <div className="user-info">
                  <img 
                    src={user?.picture || 'https://via.placeholder.com/40'} 
                    alt="Profile" 
                    className="user-avatar"
                  />
                  <span className="user-name">{user?.name}</span>
                </div>
                <button onClick={logout} className="btn btn-logout">
                  Logout
                </button>
              </div>
            ) : (
              <button onClick={login} className="btn btn-login">
                🔐 Sign in with Google
              </button>
            )}
          </div>
        </header>

        <main className="chat-area">
          <div className="messages-container">
            {messages.length === 0 || (messages.length === 1 && messages[0].id === 'welcome') ? (
              <div className="welcome-screen">
                <div className="welcome-content">
                  <div className="welcome-icon">👋</div>
                  <h2>Welcome to AI Multi-Agent Assistant!</h2>
                  <p className="welcome-subtitle">Powered by advanced AI agents to help you with multiple tasks</p>
                  
                  {/* <div className="features-grid">
                    <div className="feature-card">
                      <div className="feature-icon">📧</div>
                      <h3>Email Management</h3>
                      <p>Read, compose, and manage your emails</p>
                    </div>
                    <div className="feature-card">
                      <div className="feature-icon">📅</div>
                      <h3>Calendar</h3>
                      <p>Schedule and manage your events</p>
                    </div>
                    <div className="feature-card">
                      <div className="feature-icon">📝</div>
                      <h3>Notes & Tasks</h3>
                      <p>Create and organize your notes</p>
                    </div>
                    <div className="feature-card">
                      <div className="feature-icon">📄</div>
                      <h3>File Analysis</h3>
                      <p>Summarize and analyze documents</p>
                    </div>
                  </div> */}
                  
                  {!isAuthenticated && (
                    <div className="auth-prompt">
                      <p>🔒 Sign in with Google to unlock all features and save your chat history</p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="messages-list">
                {messages.filter(msg => msg.id !== 'welcome').map((msg) => (
                  <div 
                    key={msg.id} 
                    className={`message-wrapper ${msg.sender === 'user' ? 'user-wrapper' : 'agent-wrapper'}`}
                  >
                    {msg.sender === 'agent' && (
                      <div className="message-avatar agent-avatar">
                        {getAgentIcon(msg.agent_type)}
                      </div>
                    )}
                    
                    <div className={`message-bubble ${msg.sender === 'user' ? 'user-bubble' : 'agent-bubble'}`}>
                      {msg.sender === 'agent' && (
                        <div className="message-meta">
                          <span className="agent-name">{getAgentName(msg.agent_type)}</span>
                          {msg.agents_involved && msg.agents_involved.length > 1 && (
                            <span className="agents-badge">
                              {msg.agents_involved.length} agents
                            </span>
                          )}
                        </div>
                      )}
                      
                      <div className="message-text">
                        {msg.html_response ? (
                          <div dangerouslySetInnerHTML={{ __html: msg.html_response }} />
                        ) : (
                          <p>{msg.message}</p>
                        )}
                      </div>
                      
                      <div className="message-time">
                        {new Date(msg.timestamp).toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </div>
                    </div>

                    {msg.sender === 'user' && (
                      <div className="message-avatar user-avatar">
                        {user?.picture && !profileImageError ? (
                          <img src={user.picture} alt="You" onError={handleImageError} />
                        ) : (
                          '👤'
                        )}
                      </div>
                    )}
                  </div>
                ))}
                
                {isLoading && (
                  <div className="message-wrapper agent-wrapper">
                    <div className="message-avatar agent-avatar">🤖</div>
                    <div className="message-bubble agent-bubble typing-bubble">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <div className="input-section">
            {attachedFile && (
              <div className="file-attachment">
                <span className="file-icon">📎</span>
                <span className="file-name">{attachedFile.name}</span>
                <button onClick={removeFile} className="btn-remove-file">×</button>
              </div>
            )}
            
            <div className="input-wrapper">
              <button 
                onClick={() => fileInputRef.current?.click()} 
                className="btn-attach"
                title="Attach file"
                disabled={isLoading}
              >
                📎
              </button>
              
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={isAuthenticated ? "Type your message..." : "Sign in to start chatting..."}
                className="message-input"
                rows="1"
                disabled={isLoading || !isAuthenticated}
              />
              
              <button 
                onClick={sendMessage} 
                className="btn-send"
                disabled={isLoading || (!inputMessage.trim() && !attachedFile) || !isAuthenticated}
                title="Send message"
              >
                {isLoading ? '⏳' : '➤'}
              </button>
            </div>
          </div>
        </main>

        {/* Email Draft Icon */}
        <DraftIcon 
          sessionId={sessionId}
          onClick={handleOpenDraftList}
          isAuthenticated={isAuthenticated}
        />

        {/* Email Draft Modal */}
        {showDraftModal && currentDraft && (
          <EmailDraftModal
            draft={currentDraft}
            onClose={handleCloseDraftModal}
            onSend={handleDraftSend}
            onUpdate={handleDraftUpdate}
          />
        )}

        {/* Draft List Modal */}
        {showDraftList && (
          <DraftListModal
            sessionId={sessionId}
            onClose={() => setShowDraftList(false)}
            onSelectDraft={handleSelectDraftFromList}
          />
        )}
      </div>
    </div>
  );
}

export default App;
