import React, { useEffect, useState } from 'react';
import { useAuth } from './AuthProvider_new';

const GoogleCallback = () => {
    const { handleAuthCallback } = useAuth();
    const [status, setStatus] = useState('processing');
    const [message, setMessage] = useState('Completing authentication...');

    useEffect(() => {
        const processCallback = async () => {
            try {
                // Get code and state from URL
                const urlParams = new URLSearchParams(window.location.search);
                const code = urlParams.get('code');
                const state = urlParams.get('state');
                const error = urlParams.get('error');

                if (error) {
                    throw new Error(`OAuth error: ${error}`);
                }

                if (!code) {
                    throw new Error('No authorization code received');
                }

                setMessage('Exchanging authorization code...');

                // Exchange code for tokens
                const authData = await handleAuthCallback(code, state);

                setStatus('success');
                setMessage('Authentication successful! Redirecting...');

                // Send success message to parent window
                if (window.opener && !window.opener.closed) {
                    window.opener.postMessage(
                        {
                            type: 'auth-success',
                            access_token: authData.access_token,
                            user_profile: authData.user_profile,
                            session_id: authData.session_id
                        },
                        window.location.origin
                    );
                }

                // Close popup after a short delay
                setTimeout(() => {
                    window.close();
                }, 1000);

            } catch (err) {
                console.error('Callback processing failed:', err);
                
                setStatus('error');
                setMessage(err.message || 'Authentication failed');

                // Send error message to parent window
                if (window.opener && !window.opener.closed) {
                    window.opener.postMessage(
                        {
                            type: 'auth-error',
                            error: err.message || 'Authentication failed'
                        },
                        window.location.origin
                    );
                }

                // Close popup after a short delay
                setTimeout(() => {
                    window.close();
                }, 2000);
            }
        };

        processCallback();
    }, [handleAuthCallback]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8">
                <div className="text-center">
                    {status === 'processing' && (
                        <div className="mb-4">
                            <div className="inline-block animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                        </div>
                    )}
                    
                    {status === 'success' && (
                        <div className="mb-4">
                            <svg className="inline-block w-12 h-12 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                    )}
                    
                    {status === 'error' && (
                        <div className="mb-4">
                            <svg className="inline-block w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </div>
                    )}
                    
                    <h2 className={`text-xl font-semibold mb-2 ${
                        status === 'success' ? 'text-green-700' : 
                        status === 'error' ? 'text-red-700' : 
                        'text-gray-700'
                    }`}>
                        {status === 'processing' && 'Processing...'}
                        {status === 'success' && 'Success!'}
                        {status === 'error' && 'Error'}
                    </h2>
                    
                    <p className="text-gray-600">{message}</p>
                    
                    {status === 'error' && (
                        <button
                            onClick={() => window.close()}
                            className="mt-4 px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded text-gray-700 transition-colors"
                        >
                            Close Window
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default GoogleCallback;
