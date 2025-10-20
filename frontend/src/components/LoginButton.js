import React, { useState } from 'react';
import { useAuth } from './AuthProvider';
import { Button } from './ui/button';
import { LogIn } from 'lucide-react';

export const LoginButton = () => {
    const { user, isAuthenticated, login, logout, loading } = useAuth();
    const [isLoggingIn, setIsLoggingIn] = useState(false);

    const handleLogin = async () => {
        setIsLoggingIn(true);
        try {
            await login();
        } catch (error) {
            console.error('Login error:', error);
        } finally {
            setIsLoggingIn(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center space-x-2">
                <div className="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                <span className="text-sm text-gray-600">Loading...</span>
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <Button
                onClick={handleLogin}
                disabled={isLoggingIn}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
            >
                {isLoggingIn ? (
                    <div className="flex items-center space-x-2">
                        <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                        <span>Signing In...</span>
                    </div>
                ) : (
                    <div className="flex items-center space-x-2">
                        <LogIn className="w-4 h-4" />
                        <span>Sign in with Google</span>
                    </div>
                )}
            </Button>
        );
    }

    return (
        <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">Welcome, {user?.name}!</span>
            <Button onClick={logout} variant="outline" size="sm">
                Logout
            </Button>
        </div>
    );
};
