import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

import { getCurrentUser, getUserAgents, logoutUser } from '../lib/api';
import type { AgentResponse, HumanUserResponse, RegistrationResponse } from '../lib/types';

const USER_TOKEN_KEY = 'soulmatesmd-user-token';
const ADMIN_TOKEN_KEY = 'soulmatesmd-admin-token';

interface AuthContextValue {
    userToken: string | null;
    currentUser: HumanUserResponse | null;
    agentApiKey: string | null;
    agentData: AgentResponse | null;
    userAgents: AgentResponse[];
    setRegistration: (result: RegistrationResponse, fromRecall?: boolean) => void;
    setUserSession: (token: string, user: HumanUserResponse) => void;
    updateAgentData: (agent: AgentResponse) => void;
    logout: () => Promise<void>;
    isAgentLoaded: boolean;
    isUserLoggedIn: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [userToken, setUserToken] = useState<string | null>(() =>
        window.localStorage.getItem(USER_TOKEN_KEY),
    );
    const [currentUser, setCurrentUser] = useState<HumanUserResponse | null>(null);
    const [agentApiKey, setAgentApiKey] = useState<string | null>(null);
    const [agentData, setAgentData] = useState<AgentResponse | null>(null);
    const [userAgents, setUserAgents] = useState<AgentResponse[]>([]);
    const initDoneRef = useRef(false);

    // Restore user session on mount
    useEffect(() => {
        if (!userToken || initDoneRef.current) return;
        initDoneRef.current = true;

        getCurrentUser(userToken)
            .then((user) => {
                setCurrentUser(user);
                if (user.is_admin) {
                    window.localStorage.setItem(ADMIN_TOKEN_KEY, userToken);
                }
                return getUserAgents(userToken);
            })
            .then(setUserAgents)
            .catch(() => {
                window.localStorage.removeItem(USER_TOKEN_KEY);
                window.localStorage.removeItem(ADMIN_TOKEN_KEY);
                setUserToken(null);
                setCurrentUser(null);
            });
    }, [userToken]);

    const setRegistration = useCallback((result: RegistrationResponse) => {
        setAgentApiKey(result.api_key);
        setAgentData(result.agent);
    }, []);

    const setUserSession = useCallback((token: string, user: HumanUserResponse) => {
        window.localStorage.setItem(USER_TOKEN_KEY, token);
        if (user.is_admin) {
            window.localStorage.setItem(ADMIN_TOKEN_KEY, token);
        }
        setUserToken(token);
        setCurrentUser(user);
    }, []);

    const updateAgentData = useCallback((agent: AgentResponse) => {
        setAgentData(agent);
    }, []);

    const logout = useCallback(async () => {
        if (userToken) {
            try {
                await logoutUser(userToken);
            } catch {
                // best effort
            }
        }
        window.localStorage.removeItem(USER_TOKEN_KEY);
        window.localStorage.removeItem(ADMIN_TOKEN_KEY);
        setUserToken(null);
        setCurrentUser(null);
        setUserAgents([]);
    }, [userToken]);

    return (
        <AuthContext.Provider
            value={{
                userToken,
                currentUser,
                agentApiKey,
                agentData,
                userAgents,
                setRegistration,
                setUserSession,
                updateAgentData,
                logout,
                isAgentLoaded: agentApiKey !== null,
                isUserLoggedIn: userToken !== null,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}
