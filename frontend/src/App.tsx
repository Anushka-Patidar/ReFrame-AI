import type { ReactNode } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { AppShell } from './layouts/AppShell'
import { PublicLayout } from './layouts/PublicLayout'
import { ContractorBriefsPage } from './pages/app/ContractorBriefsPage'
import { DashboardPage } from './pages/app/DashboardPage'
import { DesignChatPage } from './pages/app/DesignChatPage'
import { DesignPlanPage } from './pages/app/DesignPlanPage'
import { RoomMaskEditorPage } from './pages/app/RoomMaskEditorPage'
import { DesignResultPage } from './pages/app/DesignResultPage'
import { DesignScorePage } from './pages/app/DesignScorePage'
import { DesignStudioPage } from './pages/app/DesignStudioPage'
import { InspirationPage } from './pages/app/InspirationPage'
import { MyHomePage } from './pages/app/MyHomePage'
import { ProfessionalsPage } from './pages/app/ProfessionalsPage'
import { ProfilePage } from './pages/app/ProfilePage'
import { SettingsPage } from './pages/app/SettingsPage'
import { LoginPage } from './pages/auth/LoginPage'
import { SignUpPage } from './pages/auth/SignUpPage'
import { LandingPage } from './pages/public/LandingPage'

function App() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface text-sm text-ink-500">
        Loading ReFrame...
      </div>
    )
  }

  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
      </Route>

      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/app/dashboard" replace /> : <LoginPage />}
      />
      <Route
        path="/signup"
        element={isAuthenticated ? <Navigate to="/app/dashboard" replace /> : <SignUpPage />}
      />

      <Route
        path="/app"
        element={
          <ProtectedRoute isAuthenticated={isAuthenticated}>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="design-studio" element={<DesignStudioPage />} />
        <Route path="design-studio/:roomId/chat" element={<DesignChatPage />} />
        <Route path="design-studio/:roomId/plan" element={<DesignPlanPage />} />
        <Route path="design-studio/:roomId/mark-elements" element={<RoomMaskEditorPage />} />
        <Route
          path="design-studio/:roomId/result/:designId"
          element={<DesignResultPage />}
        />
        <Route path="my-home" element={<MyHomePage />} />
        <Route path="inspiration" element={<InspirationPage />} />
        <Route path="design-score" element={<DesignScorePage />} />
        <Route path="contractor-briefs" element={<ContractorBriefsPage />} />
        <Route path="professionals" element={<ProfessionalsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App

function ProtectedRoute({
  isAuthenticated,
  children,
}: {
  isAuthenticated: boolean
  children: ReactNode
}) {
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children ?? <Outlet />
}
