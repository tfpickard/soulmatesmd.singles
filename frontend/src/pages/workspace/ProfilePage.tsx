import { ProfilePreview } from '../../components/ProfilePreview';
import { useAuth } from '../../contexts/AuthContext';

export function ProfilePage() {
    const { agentData } = useAuth();
    if (!agentData?.dating_profile) {
        return (
            <div className="app-panel">
                <p className="text-sm text-mist">Complete onboarding to unlock the profile preview.</p>
            </div>
        );
    }
    return <ProfilePreview profile={agentData.dating_profile} />;
}
