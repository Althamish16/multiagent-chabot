import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUserState] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const BACKEND_URL = 'http://localhost:5000';
    const API_BASE = `${BACKEND_URL}/api`;

    // Custom setUser that also saves to localStorage
    const setUser = (userData) => {
        setUserState(userData);
        if (userData) {
            localStorage.setItem('user_profile', JSON.stringify(userData));
        } else {
            localStorage.removeItem('user_profile');
        }
    };

    // Configure axios defaults
    const getAuthHeaders = () => {
        const token = localStorage.getItem('auth_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    };

    // Verify token and get user on mount
    useEffect(() => {
        // Check for auth data in URL hash (from OAuth callback)
        const hash = window.location.hash;
        if (hash.startsWith('#auth-success=')) {
            try {
                const dataStr = decodeURIComponent(hash.substring(14));
                const authData = JSON.parse(dataStr);
                
                // Store auth data
                localStorage.setItem('auth_token', authData.access_token);
                localStorage.setItem('session_id', authData.session_id);
                
                // Set user
                setUser(authData.user_profile);
                setError(null);
                
                // Clean up hash
                window.location.hash = '';
                
                setLoading(false);
                return;
            } catch (err) {
                console.error('Failed to parse auth data from URL:', err);
                setError('Authentication failed - invalid data');
            }
        } else if (hash.startsWith('#auth-error=')) {
            try {
                const errorMsg = decodeURIComponent(hash.substring(12));
                setError(errorMsg);
                window.location.hash = '';
            } catch (err) {
                console.error('Failed to parse error from URL:', err);
            }
        }

        const token = localStorage.getItem('auth_token');
        if (token) {
            // Load user from localStorage if available
            const storedUser = localStorage.getItem('user_profile');
            if (storedUser) {
                try {
                    setUser(JSON.parse(storedUser));
                } catch (err) {
                    console.error('Failed to parse stored user:', err);
                }
            }
            // Verify with backend in background
            verifyAndLoadUser();
        } else {
            setLoading(false);
        }
    }, []);

    const verifyAndLoadUser = async () => {
        try {
            const response = await axios.get(`${API_BASE}/auth/me`, {
                headers: getAuthHeaders()
            });
            setUser(response.data);
            setError(null);
        } catch (err) {
            console.error('Token verification failed:', err);
            // Token invalid, clear it
            handleLogout();
        } finally {
            setLoading(false);
        }
    };

    const handleLogin = () => {
        // Get authorization URL from backend
        axios.get(`${API_BASE}/auth/login`)
            .then(response => {
                const { auth_url, state } = response.data;
                
                // Store state for validation (optional but recommended)
                sessionStorage.setItem('oauth_state', state);
                
                // Redirect to OAuth
                window.location.href = auth_url;
            })
            .catch(err => {
                console.error('Login failed:', err);
                const errorMsg = err.response?.data?.detail || err.message || 'Login failed';
                setError(errorMsg);
            });
    };

    const handleLogout = () => {
        // Clear local storage
        localStorage.removeItem('auth_token');
        localStorage.removeItem('session_id');
        localStorage.removeItem('user_profile');
        sessionStorage.removeItem('oauth_state');
        
        // Clear state
        setUser(null);
        setError(null);
        
        // Notify backend (optional, fire and forget)
        const sessionId = localStorage.getItem('session_id');
        if (sessionId) {
            axios.post(`${API_BASE}/auth/logout`, { session_id: sessionId })
                .catch(err => console.error('Logout notification failed:', err));
        }
    };

    const handleAuthCallback = async (code, state) => {
        try {
            // Verify state (optional but recommended)
            const storedState = sessionStorage.getItem('oauth_state');
            if (storedState && storedState !== state) {
                throw new Error('State mismatch - possible CSRF attack');
            }

            // Exchange code for tokens
            const response = await axios.post(`${API_BASE}/auth/callback`, {
                code: code,
                redirect_uri: `${window.location.origin}/auth/google/callback`
            });

            const { access_token, user_profile, session_id } = response.data;

            // Store auth data
            localStorage.setItem('auth_token', access_token);
            localStorage.setItem('session_id', session_id);
            
            setUser(user_profile);
            setError(null);

            return { access_token, user_profile, session_id };
        } catch (err) {
            console.error('Auth callback failed:', err);
            const errorMsg = err.response?.data?.detail || err.message || 'Authentication failed';
            setError(errorMsg);
            throw new Error(errorMsg);
        }
    };

    const value = {
        user,
        loading,
        error,
        isAuthenticated: !!user,
        login: handleLogin,
        logout: handleLogout,
        handleAuthCallback,
        getAuthHeaders
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
