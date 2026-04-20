import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { apiFetch, ApiError } from "../../lib/api";
import { useAuth } from "./AuthContext";

export function ChangePasswordPage() {
  const { session, refreshMe } = useAuth();
  const [form, setForm] = useState({ current_password: "", new_password: "" });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  if (!session.user.must_change_password) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await apiFetch("/api/auth/change-password/", {
        method: "POST",
        body: JSON.stringify(form),
      }, session);
      setMessage("Password updated.");
      await refreshMe();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to change password.");
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-panel">
        <p className="eyebrow">Security</p>
        <h1>Change your password</h1>
        <p>This account requires a password update before you can continue using the workspace.</p>
        <form className="form-grid" onSubmit={onSubmit}>
          <label>
            Current password
            <input
              type="password"
              value={form.current_password}
              onChange={(event) => setForm({ ...form, current_password: event.target.value })}
            />
          </label>
          <label>
            New password
            <input
              type="password"
              value={form.new_password}
              onChange={(event) => setForm({ ...form, new_password: event.target.value })}
            />
          </label>
          {message ? <p className="form-success">{message}</p> : null}
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" type="submit">
            Update password
          </button>
        </form>
      </div>
    </div>
  );
}

