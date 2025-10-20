import React, { useEffect } from 'react';
import { useAuth } from '../components/AuthProvider';

const GoogleCallback = () => {
    const { handleAuthCallback } = useAuth();

    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const error = urlParams.get('error');

        if (error) {
            console.error('OAuth error:', error);
            window.close();
            return;
        }

        if (code) {
            handleAuthCallback(code)
                .then(() => {
                    // Send success message to parent window
                    if (window.opener) {
                        window.opener.postMessage({ type: 'auth-success' }, window.location.origin);
                    }
                    window.close();
                })
                .catch(error => {
                    console.error('Auth callback error:', error);
                    if (window.opener) {
                        window.opener.postMessage({ type: 'auth-error', error }, window.location.origin);
                    }
                    window.close();
                });
        }
    }, [handleAuthCallback]);

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-100">
            <div className="bg-white p-8 rounded-lg shadow-md">
                <div className="flex items-center space-x-4">
                    <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
                    <span className="text-gray-700">Completing sign-in...</span>
                </div>
            </div>
        </div>
    );
};

export default GoogleCallback;