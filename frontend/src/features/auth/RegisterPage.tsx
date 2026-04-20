import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../../lib/api";
import { useAuth } from "./AuthContext";

const initialForm = {
  username: "",
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  organization_name: "",
};

export function RegisterPage() {
  const navigate = useNavigate();
  const { register, session } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState<string | null>(null);

  if (session) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await register(form);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to register.");
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-panel wide">
        <p className="eyebrow">Workspace Setup</p>
        <h1>Create the first organization</h1>
        <p>This flow bootstraps the initial admin account and the first organization membership.</p>

        <form className="form-grid two-column" onSubmit={onSubmit}>
          <label>
            Organization name
            <input value={form.organization_name} onChange={(event) => setForm({ ...form, organization_name: event.target.value })} />
          </label>
          <label>
            Username
            <input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} />
          </label>
          <label>
            First name
            <input value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} />
          </label>
          <label>
            Last name
            <input value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} />
          </label>
          <label>
            Email
            <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
          </label>
          {error ? <p className="form-error span-2">{error}</p> : null}
          <button className="primary-button span-2" type="submit">
            Create workspace
          </button>
        </form>

        <p className="auth-link">
          Already have access? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

