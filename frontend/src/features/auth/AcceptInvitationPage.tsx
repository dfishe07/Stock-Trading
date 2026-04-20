import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiFetch, ApiError } from "../../lib/api";
import type { Invitation } from "../../lib/types";

export function AcceptInvitationPage() {
  const [searchParams] = useSearchParams();
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState({
    username: "",
    password: "",
    first_name: "",
    last_name: "",
  });

  const token = searchParams.get("token") ?? "";

  useEffect(() => {
    if (!token) {
      return;
    }
    apiFetch<Invitation>(`/api/auth/invitation-lookup/?token=${token}`)
      .then(setInvitation)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Invitation not found."));
  }, [token]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await apiFetch("/api/auth/accept-invitation/", {
        method: "POST",
        body: JSON.stringify({ token, ...form }),
      });
      setSuccess("Invitation accepted. Sign in and change your password on first login.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to accept invitation.");
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-panel wide">
        <p className="eyebrow">Invitation</p>
        <h1>Activate your account</h1>
        {invitation ? (
          <p>
            You were invited to <strong>{invitation.organization.name}</strong> as a <strong>{invitation.role}</strong>.
          </p>
        ) : (
          <p>Validating invitation token.</p>
        )}

        <form className="form-grid two-column" onSubmit={onSubmit}>
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
          <label>
            First name
            <input value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} />
          </label>
          <label>
            Last name
            <input value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} />
          </label>
          {error ? <p className="form-error span-2">{error}</p> : null}
          {success ? <p className="form-success span-2">{success}</p> : null}
          <button className="primary-button span-2" type="submit">
            Activate account
          </button>
        </form>

        <p className="auth-link">
          Already active? <Link to="/login">Return to sign in</Link>
        </p>
      </div>
    </div>
  );
}

