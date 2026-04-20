import { Card } from "../../components/Card";
import { PageHeader } from "../../components/PageHeader";
import { useAuth } from "../auth/AuthContext";

export function OverviewPage() {
  const { session } = useAuth();

  return (
    <div className="stack-xl">
      <PageHeader
        eyebrow="Platform Overview"
        title="Foundation for a trading operating system"
        description="The platform now covers identity, versioned strategy design, historical backtesting, and paper-trading operations with shared engine rules and organization-scoped controls."
      />

      <section className="summary-grid">
        <Card title="Access control">
          <p>Signed in as {session?.user.username} with {session?.user.memberships[0]?.role ?? "user"} access.</p>
        </Card>
        <Card title="Strategy system">
          <p>Declarative JSON strategies with immutable versions, deterministic validation, and publish-ready lifecycle states.</p>
        </Card>
        <Card title="Trading model">
          <p>Paper broker accounts, deployment heartbeats, positions, orders, and event telemetry are now wired into the same execution contract used by backtests.</p>
        </Card>
      </section>
    </div>
  );
}
