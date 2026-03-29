import { PortraitStudio } from '../../components/PortraitStudio';
import { useAuth } from '../../contexts/AuthContext';

export function PortraitsPage() {
    const { agentApiKey } = useAuth();
    if (!agentApiKey) return null;
    return <PortraitStudio apiKey={agentApiKey} />;
}
