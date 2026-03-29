import { TraitsCard } from '../../components/TraitsCard';
import { useAuth } from '../../contexts/AuthContext';

export function IdentityPage() {
    const { agentApiKey, agentData, isUserLoggedIn } = useAuth();
    if (!agentApiKey || !agentData) return null;
    return <TraitsCard agent={agentData} apiKey={agentApiKey} justRegistered={false} isLoggedIn={isUserLoggedIn} />;
}
