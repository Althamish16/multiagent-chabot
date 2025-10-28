import React, { useState } from 'react';
import { useAuth } from './AuthProvider_new';
import { Button } from './ui/button';
import { LogIn, LogOut, User } from 'lucide-react';

export const LoginButton = () => {
    const { user, isAuthenticated, loading, login, logout, error } = useAuth();
    const [isLoggingIn, setIsLoggingIn] = useState(false);
    const [profileImageError, setProfileImageError] = useState(false);

    const handleLogin = async () => {
        setIsLoggingIn(true);
        try {
            await login();
        } catch (err) {
            console.error('Login error:', err);
            // Error is handled in AuthProvider
        } finally {
            setIsLoggingIn(false);
        }
    };

    const handleLogout = () => {
        logout();
        setProfileImageError(false); // Reset error state on logout
    };

    const handleImageError = async () => {
        setProfileImageError(true);
        
        // Note: Removed refreshProfile call as it won't fix broken image URLs
        // The profile refresh is for updating user data, not fixing image loading issues
    };

    if (loading) {
        return (
            <Button disabled variant="outline">
                <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mr-2"></div>
                Loading...
            </Button>
        );
    }

    if (isAuthenticated && user) {
        return (
            <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                    {user.picture && !profileImageError ? (
                        <img 
                            src={user.picture} 
                            alt={user.name}
                            className="w-8 h-8 rounded-full"
                            onError={handleImageError}
                        />
                    ) : (
                        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                            <User className="w-5 h-5 text-white" />
                        </div>
                    )}
                    <div className="text-sm">
                        <div className="font-medium">{user.name}</div>
                        <div className="text-gray-500 text-xs">{user.email}</div>
                    </div>
                </div>
                <Button 
                    onClick={handleLogout}
                    variant="outline"
                    size="sm"
                >
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center gap-2">
            <Button 
                onClick={handleLogin}
                disabled={isLoggingIn}
                className="bg-blue-600 hover:bg-blue-700 text-white"
            >
                {isLoggingIn ? (
                    <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                        Signing in...
                    </>
                ) : (
                    <>
                        <LogIn className="w-4 h-4 mr-2" />
                        Sign in with Google
                    </>
                )}
            </Button>
            {error && (
                <p className="text-xs text-red-500 text-center max-w-xs">
                    {error}
                </p>
            )}
        </div>
    );
};
