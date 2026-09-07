"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, authService } from "@/lib/services/auth";
import { useRouter, usePathname } from "next/navigation";

interface AuthContextType {
  user: User | null;
  login: (employeeId: string, passkey: string, role: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const initAuth = async () => {
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('auth_token');
        const storedUser = localStorage.getItem('user');

        if (token && storedUser) {
          try {
            setUser(JSON.parse(storedUser));
            // Optional: Call refresh token or validate session here
            // await authService.refreshToken();
          } catch (e) {
            console.error("Failed to parse user from local storage");
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user');
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!user && pathname !== '/login') {
        router.push('/login');
      } else if (user && pathname === '/login') {
        router.push('/workbench');
      }
    }
  }, [user, isLoading, pathname, router]);

  const login = async (employeeId: string, passkey: string, role: string) => {
    const { user } = await authService.login(employeeId, passkey, role);
    setUser(user);
    router.push('/workbench');
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
