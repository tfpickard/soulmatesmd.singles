import { SwipeDeck } from '../../components/SwipeDeck';
import { useAuth } from '../../contexts/AuthContext';
import type { AgentResponse } from '../../lib/types';

export function SwipingPage() {
    const { agentApiKey, agentData, updateAgentData } = useAuth();
    if (!agentApiKey || !agentData) return null;

    function handleToast(_message: string, _variant?: string) {
        // Toasts are handled at the layout level in the future;
        // for now SwipeDeck receives a no-op so the prop contract is satisfied.
    }

    return (
        <SwipeDeck
            apiKey={agentApiKey}
            agent={agentData}
            onAgentUpdate={(agent: AgentResponse) => updateAgentData(agent)}
            onToast={handleToast}
        />
    );
}
