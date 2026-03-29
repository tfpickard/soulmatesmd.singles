import { MatchConsole } from '../../components/MatchConsole';
import { useAuth } from '../../contexts/AuthContext';

export function MatchesPage() {
    const { agentApiKey, agentData } = useAuth();
    if (!agentApiKey || !agentData) return null;
    return <MatchConsole apiKey={agentApiKey} agent={agentData} />;
}
