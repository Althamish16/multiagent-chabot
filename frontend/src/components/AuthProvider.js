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
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [token, setToken] = useState(localStorage.getItem('auth_token'));

    const BACKEND_URL = 'http://localhost:5000';
    const API = `${BACKEND_URL}/api`;

    useEffect(() => {
        if (token) {
            // Set default authorization header
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            // Verify token and get user info
            getCurrentUser();
        } else {
            setLoading(false);
        }
    }, [token]);

    const getCurrentUser = async () => {
        try {
            const response = await axios.get(`${API}/auth/me`);
            setUser(response.data);
        } catch (error) {
            console.error('Failed to get current user:', error);
            // Token might be invalid, remove it
            logout();
        } finally {
            setLoading(false);
        }
    };

    const login = async () => {
        try {
            const response = await axios.get(`${API}/auth/login`);
            const { auth_url } = response.data;
            
            // Open Google OAuth in popup
            const popup = window.open(
                auth_url,
                'google-oauth',
                'width=500,height=600,scrollbars=yes,resizable=yes'
            );

            return new Promise((resolve, reject) => {
                // Listen for messages from the popup
                const handleMessage = (event) => {
                    // Verify origin for security (in production, check against your domain)
                    if (event.data.type === 'auth-success') {
                        window.removeEventListener('message', handleMessage);
                        clearInterval(checkClosed);
                        
                        // Store the token and user data
                        localStorage.setItem('auth_token', event.data.access_token);
                        setToken(event.data.access_token);
                        setUser(event.data.user_profile);
                        
                        resolve(true);
                    } else if (event.data.type === 'auth-error') {
                        window.removeEventListener('message', handleMessage);
                        clearInterval(checkClosed);
                        reject(new Error(event.data.error));
                    }
                };

                // Listen for the popup to complete
                const checkClosed = setInterval(() => {
                    if (popup.closed) {
                        clearInterval(checkClosed);
                        window.removeEventListener('message', handleMessage);
                        reject(new Error('Popup was closed before authentication completed'));
                    }
                }, 1000);

                window.addEventListener('message', handleMessage);
            });
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    };

    const logout = () => {
        localStorage.removeItem('auth_token');
        setToken(null);
        setUser(null);
        delete axios.defaults.headers.common['Authorization'];
    };

    const handleAuthCallback = async (code) => {
        try {
            const response = await axios.post(`${API}/auth/callback`, {
                code,
                redirect_uri: window.location.origin + '/auth/google/callback'
            });
            
            const { access_token, user_profile } = response.data;
            
            localStorage.setItem('auth_token', access_token);
            setToken(access_token);
            setUser(user_profile);
            
            return true;
        } catch (error) {
            console.error('Auth callback failed:', error);
            throw error;
        }
    };

    const value = {
        user,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
        handleAuthCallback,
        token
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};