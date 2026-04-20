import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../../lib/api";
import { useAuth } from "./AuthContext";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, session } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState<string | null>(null);

  if (session) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await login(form);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to sign in.");
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-panel">
        <p className="eyebrow">Phase 1 Foundation</p>
        <h1>Trading platform access</h1>
        <p>Sign in with your platform account. Admins can invite new users from the admin workspace after registration.</p>

        <form className="form-grid" onSubmit={onSubmit}>
          <label>
            Username
            <input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" type="submit">
            Sign in
          </button>
        </form>

        <p className="auth-link">
          Need a workspace? <Link to="/register">Create the first organization</Link>
        </p>
      </div>
    </div>
  );
}

