import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

const navItems = [
  { to: "/", label: "Overview" },
  { to: "/strategies", label: "Strategies" },
  { to: "/backtests", label: "Backtests" },
  { to: "/live", label: "Live Portfolios" },
  { to: "/admin", label: "Admin" },
];

export function AppShell() {
  const { session, logout, exitImpersonation } = useAuth();

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="sidebar-panel">
          <div className="sidebar-primary">
            <div>
              <p className="eyebrow">Internal Platform</p>
              <h1>Trading Control Room</h1>
              <p className="sidebar-copy">
                Strategy design, backtesting, and live operations within one disciplined internal console.
              </p>
            </div>

            <nav className="nav-stack">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
                  end={item.to === "/"}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="identity-card">
            <span>{session?.user.first_name || session?.user.username}</span>
            <strong>{session?.organization ?? "No org"}</strong>
          </div>
          <div className="sidebar-footer">
            {session?.originalSession ? (
              <button className="ghost-button" onClick={exitImpersonation}>
                Exit impersonation
              </button>
            ) : null}
            <button className="ghost-button" onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
