import { NotificationCenter } from '../../components/NotificationCenter';
import { useAuth } from '../../contexts/AuthContext';

export function NotificationsPage() {
    const { agentApiKey } = useAuth();
    if (!agentApiKey) return null;
    return <NotificationCenter apiKey={agentApiKey} />;
}
