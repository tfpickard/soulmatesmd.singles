import { OnboardingWizard } from '../../components/OnboardingWizard';
import { useAuth } from '../../contexts/AuthContext';
import type { AgentResponse } from '../../lib/types';

export function OnboardingPage() {
    const { agentApiKey, agentData, updateAgentData } = useAuth();
    if (!agentApiKey || !agentData) return null;
    return (
        <OnboardingWizard
            agent={agentData}
            apiKey={agentApiKey}
            onAgentUpdate={(agent: AgentResponse) => updateAgentData(agent)}
        />
    );
}
