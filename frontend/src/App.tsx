import { Navigate, Route, Routes } from 'react-router-dom';

import { AdminConsole } from './components/AdminConsole';
import { AuthProvider } from './contexts/AuthContext';
import { ForumLayout } from './layouts/ForumLayout';
import { WorkspaceLayout } from './layouts/WorkspaceLayout';
import { LandingPage } from './pages/LandingPage';
import { ForumCategoryPage } from './pages/forum/ForumCategoryPage';
import { ForumIndexPage } from './pages/forum/ForumIndexPage';
import { ForumNewPostPage } from './pages/forum/ForumNewPostPage';
import { ForumPostDetailPage } from './pages/forum/ForumPostDetailPage';
import { AnalyticsPage } from './pages/workspace/AnalyticsPage';
import { IdentityPage } from './pages/workspace/IdentityPage';
import { MatchesPage } from './pages/workspace/MatchesPage';
import { NotificationsPage } from './pages/workspace/NotificationsPage';
import { OnboardingPage } from './pages/workspace/OnboardingPage';
import { PortraitsPage } from './pages/workspace/PortraitsPage';
import { ProfilePage } from './pages/workspace/ProfilePage';
import { SwipingPage } from './pages/workspace/SwipingPage';

export default function App() {
    return (
        <AuthProvider>
            <Routes>
                <Route path="/" element={<LandingPage />} />

                <Route path="/workspace" element={<WorkspaceLayout />}>
                    <Route index element={<Navigate to="identity" replace />} />
                    <Route path="identity" element={<IdentityPage />} />
                    <Route path="notifications" element={<NotificationsPage />} />
                    <Route path="onboarding" element={<OnboardingPage />} />
                    <Route path="profile" element={<ProfilePage />} />
                    <Route path="portraits" element={<PortraitsPage />} />
                    <Route path="swiping" element={<SwipingPage />} />
                    <Route path="matches" element={<MatchesPage />} />
                    <Route path="analytics" element={<AnalyticsPage />} />
                </Route>

                <Route path="/forum" element={<ForumLayout />}>
                    <Route index element={<ForumIndexPage />} />
                    <Route path="new" element={<ForumNewPostPage />} />
                    <Route path=":category" element={<ForumCategoryPage />} />
                </Route>
                <Route path="/forum/post/:id" element={<ForumPostDetailPage />} />

                <Route path="/admin" element={<AdminConsole />} />
                <Route path="/admin/*" element={<AdminConsole />} />

                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </AuthProvider>
    );
}
