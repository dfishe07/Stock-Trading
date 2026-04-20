import { FormEvent, useEffect, useState } from "react";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch, ApiError } from "../../lib/api";
import type { Invitation, User } from "../../lib/types";
import { useAuth } from "../auth/AuthContext";

export function AdminPage() {
  const { session, acceptImpersonation } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "user" });
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    if (!session) {
      return;
    }
    const [userPayload, invitationPayload] = await Promise.all([
      apiFetch<User[]>("/api/auth/users/", {}, session),
      apiFetch<Invitation[]>("/api/auth/invitations/", {}, session),
    ]);
    setUsers(userPayload);
    setInvitations(invitationPayload);
  };

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load admin data."));
  }, []);

  const sendInvite = async (event: FormEvent) => {
    event.preventDefault();
    if (!session) {
      return;
    }
    try {
      await apiFetch(
        "/api/auth/invitations/",
        {
          method: "POST",
          body: JSON.stringify(inviteForm),
        },
        session,
      );
      setInviteForm({ email: "", role: "user" });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to send invitation.");
    }
  };

  const impersonate = async (user: User) => {
    if (!session) {
      return;
    }
    const response = await apiFetch<{ token: string; audit_id: string; user: User }>(
      "/api/auth/users/impersonate/",
      {
        method: "POST",
        body: JSON.stringify({ user_id: user.id, reason: "Operational support" }),
      },
      session,
    );
    acceptImpersonation({ token: response.token, auditId: response.audit_id, user: response.user });
  };

  return (
    <div className="stack-xl">
      <PageHeader
        eyebrow="Administration"
        title="Users, invitations, and support controls"
        description="Phase 1 includes workspace invitations, role-aware access, and an audited impersonation entry point for admin troubleshooting."
      />
      {error ? <p className="form-error">{error}</p> : null}

      <section className="split-grid">
        <Card title="Invite a teammate">
          <form className="form-grid" onSubmit={sendInvite}>
            <label>
              Email
              <input value={inviteForm.email} onChange={(event) => setInviteForm({ ...inviteForm, email: event.target.value })} />
            </label>
            <label>
              Role
              <select value={inviteForm.role} onChange={(event) => setInviteForm({ ...inviteForm, role: event.target.value })}>
                <option value="user">user</option>
                <option value="developer">developer</option>
                <option value="admin">admin</option>
              </select>
            </label>
            <button className="primary-button" type="submit">
              Send invitation
            </button>
          </form>
        </Card>

        <Card title="Current users">
          <div className="stack-md">
            {users.length === 0 ? (
              <EmptyState title="No users found" description="Invited and registered users will appear here." />
            ) : (
              users.map((user) => (
                <div key={user.id} className="user-row">
                  <div>
                    <strong>{user.first_name || user.username}</strong>
                    <p>{user.email}</p>
                  </div>
                  <div className="user-row-actions">
                    <span className="pill">{user.memberships[0]?.role ?? "user"}</span>
                    {session?.user.id !== user.id ? (
                      <button className="ghost-button" onClick={() => impersonate(user)}>
                        Login as
                      </button>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </section>

      <Card title="Invitations">
        <div className="stack-md">
          {invitations.length === 0 ? (
            <EmptyState title="No invitations yet" description="New invitations will be listed here with their current status." />
          ) : (
            invitations.map((invitation) => (
              <div key={invitation.id} className="invitation-row">
                <div>
                  <strong>{invitation.email}</strong>
                  <p>
                    {invitation.role} • {invitation.status}
                  </p>
                </div>
                <small>{new Date(invitation.expires_at).toLocaleString()}</small>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

