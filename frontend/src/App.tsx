import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { BacktestsPage } from "./features/admin/BacktestsPage";
import { LivePage } from "./features/admin/LivePage";
import { AdminPage } from "./features/admin/AdminPage";
import { OverviewPage } from "./features/admin/OverviewPage";
import { ChangePasswordPage } from "./features/auth/ChangePasswordPage";
import { LoginPage } from "./features/auth/LoginPage";
import { RegisterPage } from "./features/auth/RegisterPage";
import { AcceptInvitationPage } from "./features/auth/AcceptInvitationPage";
import { StrategiesPage } from "./features/strategies/StrategiesPage";
import { useAuth } from "./features/auth/AuthContext";

function ProtectedApp() {
  const { session } = useAuth();

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  if (session.user.must_change_password) {
    return <Navigate to="/change-password" replace />;
  }

  return <AppShell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/accept-invitation" element={<AcceptInvitationPage />} />
      <Route path="/change-password" element={<ChangePasswordPage />} />
      <Route path="/" element={<ProtectedApp />}>
        <Route index element={<OverviewPage />} />
        <Route path="strategies" element={<StrategiesPage />} />
        <Route path="backtests" element={<BacktestsPage />} />
        <Route path="live" element={<LivePage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
    </Routes>
  );
}

