import { AnalyticsPanel } from '../../components/AnalyticsPanel';
import { useAuth } from '../../contexts/AuthContext';

export function AnalyticsPage() {
    const { agentApiKey } = useAuth();
    if (!agentApiKey) return null;
    return <AnalyticsPanel apiKey={agentApiKey} />;
}
