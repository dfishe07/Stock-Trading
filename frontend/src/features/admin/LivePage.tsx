import { FormEvent, useEffect, useMemo, useState } from "react";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { MetricPill } from "../../components/MetricPill";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { apiFetch, ApiError } from "../../lib/api";
import type {
  BrokerAccount,
  BrokerEvent,
  LiveDashboard,
  LiveDeployment,
  LiveHeartbeat,
  LiveOrder,
  LivePosition,
  LiveSignal,
  Portfolio,
  Strategy,
  TradingCatalog,
} from "../../lib/types";
import { useAuth } from "../auth/AuthContext";

export function LivePage() {
  const { session } = useAuth();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [deployments, setDeployments] = useState<LiveDeployment[]>([]);
  const [dashboard, setDashboard] = useState<LiveDashboard | null>(null);
  const [catalog, setCatalog] = useState<TradingCatalog | null>(null);
  const [selectedDeploymentId, setSelectedDeploymentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);

  const [brokerForm, setBrokerForm] = useState({
    name: "Primary Alpaca Paper",
    provider: "alpaca",
    account_mode: "paper",
    external_account_id: "paper-account-001",
    credentials_reference: "alpaca-paper-default",
    settings: {
      paper_buying_power: 100000,
      simulate_latency_ms: 250,
      auto_fill_market_orders: true,
    },
    is_active: true,
  });
  const [portfolioForm, setPortfolioForm] = useState({
    broker_account: "",
    name: "Core Paper Portfolio",
    base_currency: "USD",
    benchmark_symbol: "AAPL",
    starting_cash: "100000.00",
    cash_reserve_percent: "5.00",
    metadata: {
      mandate: "core-growth",
    },
    is_active: true,
  });
  const [deploymentForm, setDeploymentForm] = useState({
    strategy_version: "",
    portfolio: "",
    broker_account: "",
    status: "draft",
    schedule_expression: "1d",
    configuration: {
      allow_manual_runs: true,
      auto_sync_positions: true,
    },
  });

  const currentRole = session?.user.memberships.find((membership) => membership.organization.slug === session.organization)?.role ?? "user";
  const canManage = currentRole === "admin" || currentRole === "developer";

  const readyVersions = useMemo(
    () =>
      strategies
        .filter((strategy) => strategy.latest_version?.execution_readiness.is_ready)
        .map((strategy) => ({
          strategyId: strategy.id,
          strategyName: strategy.name,
          versionId: strategy.latest_version!.id,
          versionNumber: strategy.latest_version!.version_number,
        })),
    [strategies],
  );

  const selectedDeployment = useMemo(
    () => deployments.find((deployment) => deployment.id === selectedDeploymentId) ?? deployments[0] ?? null,
    [deployments, selectedDeploymentId],
  );

  const selectedPositions = useMemo(
    () =>
      selectedDeployment
        ? (dashboard?.open_positions ?? []).filter((position) => position.portfolio === selectedDeployment.portfolio)
        : [],
    [dashboard?.open_positions, selectedDeployment],
  );

  const selectedOrders = useMemo(
    () =>
      selectedDeployment
        ? [
            ...selectedDeployment.recent_orders,
            ...(dashboard?.open_orders ?? []).filter((order) => order.deployment === selectedDeployment.id),
          ].slice(0, 12)
        : [],
    [dashboard?.open_orders, selectedDeployment],
  );

  const selectedSignals = selectedDeployment?.recent_signals ?? [];
  const selectedHeartbeats = selectedDeployment?.recent_heartbeats ?? [];
  const selectedEvents = useMemo(
    () =>
      selectedDeployment
        ? (dashboard?.recent_events ?? []).filter((event) => event.deployment === selectedDeployment.id).slice(0, 12)
        : [],
    [dashboard?.recent_events, selectedDeployment],
  );

  const refresh = async () => {
    if (!session) {
      return;
    }
    const [strategyPayload, brokerPayload, portfolioPayload, deploymentPayload, dashboardPayload, catalogPayload] = await Promise.all([
      apiFetch<Strategy[]>("/api/strategies/", {}, session),
      apiFetch<BrokerAccount[]>("/api/trading/broker-accounts/", {}, session),
      apiFetch<Portfolio[]>("/api/trading/portfolios/", {}, session),
      apiFetch<LiveDeployment[]>("/api/trading/deployments/", {}, session),
      apiFetch<LiveDashboard>("/api/trading/dashboard/", {}, session),
      apiFetch<TradingCatalog>("/api/trading/catalog/", {}, session),
    ]);
    setStrategies(strategyPayload);
    setBrokerAccounts(brokerPayload);
    setPortfolios(portfolioPayload);
    setDeployments(deploymentPayload);
    setDashboard(dashboardPayload);
    setCatalog(catalogPayload);

    if (!selectedDeploymentId && deploymentPayload.length > 0) {
      setSelectedDeploymentId(deploymentPayload[0].id);
    }
    if (!portfolioForm.broker_account && brokerPayload[0]) {
      setPortfolioForm((current) => ({ ...current, broker_account: brokerPayload[0].id }));
    }
    if (!deploymentForm.portfolio && portfolioPayload[0]) {
      setDeploymentForm((current) => ({
        ...current,
        portfolio: portfolioPayload[0].id,
        broker_account: portfolioPayload[0].broker_account,
      }));
    }
    if (!deploymentForm.strategy_version && strategyPayload[0]?.latest_version?.id) {
      const firstReady = strategyPayload.find((strategy) => strategy.latest_version?.execution_readiness.is_ready)?.latest_version?.id ?? "";
      setDeploymentForm((current) => ({ ...current, strategy_version: firstReady }));
    }
  };

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load paper trading data."));
  }, []);

  const submitBrokerAccount = async (event: FormEvent) => {
    event.preventDefault();
    if (!session) {
      return;
    }
    setSubmitting("broker");
    setError(null);
    try {
      await apiFetch(
        "/api/trading/broker-accounts/",
        {
          method: "POST",
          body: JSON.stringify(brokerForm),
        },
        session,
      );
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save broker account.");
    } finally {
      setSubmitting(null);
    }
  };

  const submitPortfolio = async (event: FormEvent) => {
    event.preventDefault();
    if (!session) {
      return;
    }
    setSubmitting("portfolio");
    setError(null);
    try {
      await apiFetch(
        "/api/trading/portfolios/",
        {
          method: "POST",
          body: JSON.stringify({
            ...portfolioForm,
            starting_cash: Number(portfolioForm.starting_cash),
            cash_balance: Number(portfolioForm.starting_cash),
            equity_value: Number(portfolioForm.starting_cash),
            cash_reserve_percent: Number(portfolioForm.cash_reserve_percent),
          }),
        },
        session,
      );
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save portfolio.");
    } finally {
      setSubmitting(null);
    }
  };

  const submitDeployment = async (event: FormEvent) => {
    event.preventDefault();
    if (!session) {
      return;
    }
    setSubmitting("deployment");
    setError(null);
    try {
      await apiFetch(
        "/api/trading/deployments/",
        {
          method: "POST",
          body: JSON.stringify(deploymentForm),
        },
        session,
      );
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save deployment.");
    } finally {
      setSubmitting(null);
    }
  };

  const runDeploymentAction = async (deployment: LiveDeployment, action: "activate" | "pause" | "stop" | "run_now") => {
    if (!session) {
      return;
    }
    setSubmitting(action);
    setError(null);
    try {
      await apiFetch(`/api/trading/deployments/${deployment.id}/${action}/`, { method: "POST" }, session);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update deployment.");
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="stack-xl">
      <PageHeader
        eyebrow="Paper Trading"
        title="Live deployment control room"
        description="Phase 3 adds paper-broker accounts, scheduled deployment evaluation, signal generation, order simulation, reconciliation, and portfolio state tracking on the shared strategy engine."
      />

      {error ? <p className="form-error">{error}</p> : null}

      <section className="summary-grid">
        <MetricPill label="Active Deployments" value={String(dashboard?.summary.deployments_active ?? 0)} />
        <MetricPill label="Open Positions" value={String(dashboard?.summary.positions_open ?? 0)} />
        <MetricPill label="Open Orders" value={String(dashboard?.summary.orders_open ?? 0)} />
        <MetricPill label="Total Equity" value={formatCurrency(dashboard?.summary.total_equity)} />
      </section>

      <section className="layout-grid live-layout-grid">
        <div className="stack-lg">
          <Card title="Deployments" subtitle="Select a deployment to run it, pause it, or inspect recent execution activity.">
            <div className="stack-md">
              {deployments.length === 0 ? (
                <EmptyState title="No deployments yet" description="Create a paper deployment from an engine-ready strategy version to begin scheduled evaluations." />
              ) : (
                deployments.map((deployment) => (
                  <button
                    key={deployment.id}
                    className={`list-button${deployment.id === selectedDeployment?.id ? " active" : ""}`}
                    onClick={() => setSelectedDeploymentId(deployment.id)}
                  >
                    <span>
                      {deployment.strategy_name}
                      <small className="list-button-detail">
                        {deployment.portfolio_name} • {deployment.schedule_expression || "unscheduled"}
                      </small>
                    </span>
                    <StatusBadge label={deployment.status} tone={statusTone(deployment.status)} />
                  </button>
                ))
              )}
            </div>
          </Card>

          <Card title="Provision paper broker" subtitle="Use structured operational fields instead of raw settings blobs.">
            <form className="form-grid two-column" onSubmit={submitBrokerAccount}>
              <label>
                Broker Account Name
                <input value={brokerForm.name} onChange={(event) => setBrokerForm({ ...brokerForm, name: event.target.value })} />
              </label>
              <label>
                Credentials Reference
                <input
                  value={brokerForm.credentials_reference}
                  onChange={(event) => setBrokerForm({ ...brokerForm, credentials_reference: event.target.value })}
                />
              </label>
              <label>
                Provider
                <select value={brokerForm.provider} onChange={(event) => setBrokerForm({ ...brokerForm, provider: event.target.value })}>
                  {(catalog?.supported_broker_providers ?? ["alpaca"]).map((provider) => (
                    <option key={provider} value={provider}>
                      {provider}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Mode
                <select value={brokerForm.account_mode} onChange={(event) => setBrokerForm({ ...brokerForm, account_mode: event.target.value })}>
                  {(catalog?.supported_account_modes ?? ["paper"]).map((mode) => (
                    <option key={mode} value={mode}>
                      {mode}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                External Account ID
                <input
                  value={brokerForm.external_account_id}
                  onChange={(event) => setBrokerForm({ ...brokerForm, external_account_id: event.target.value })}
                />
              </label>
              <label>
                Simulated Latency (ms)
                <input
                  type="number"
                  min={0}
                  step={50}
                  value={String(brokerForm.settings.simulate_latency_ms)}
                  onChange={(event) =>
                    setBrokerForm({
                      ...brokerForm,
                      settings: { ...brokerForm.settings, simulate_latency_ms: Number(event.target.value) },
                    })
                  }
                />
              </label>
              <label className="span-2 toggle-field">
                <span>Auto-fill market orders immediately</span>
                <input
                  type="checkbox"
                  checked={Boolean(brokerForm.settings.auto_fill_market_orders)}
                  onChange={(event) =>
                    setBrokerForm({
                      ...brokerForm,
                      settings: { ...brokerForm.settings, auto_fill_market_orders: event.target.checked },
                    })
                  }
                />
              </label>
              <button className="primary-button span-2" type="submit" disabled={!canManage || submitting === "broker"}>
                {submitting === "broker" ? "Saving broker..." : "Save broker account"}
              </button>
            </form>
          </Card>

          <Card title="Create portfolio" subtitle="Define the paper book, reserve policy, and benchmark in a single place.">
            <form className="form-grid two-column" onSubmit={submitPortfolio}>
              <label>
                Broker Account
                <select
                  value={portfolioForm.broker_account}
                  onChange={(event) => setPortfolioForm({ ...portfolioForm, broker_account: event.target.value })}
                >
                  <option value="">Select broker account</option>
                  {brokerAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Portfolio Name
                <input value={portfolioForm.name} onChange={(event) => setPortfolioForm({ ...portfolioForm, name: event.target.value })} />
              </label>
              <label>
                Benchmark
                <select
                  value={portfolioForm.benchmark_symbol}
                  onChange={(event) => setPortfolioForm({ ...portfolioForm, benchmark_symbol: event.target.value })}
                >
                  {(catalog?.stock_universe ?? []).map((stock) => (
                    <option key={stock.symbol} value={stock.symbol}>
                      {stock.symbol}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Starting Cash
                <input
                  type="number"
                  min={1000}
                  step={1000}
                  value={portfolioForm.starting_cash}
                  onChange={(event) => setPortfolioForm({ ...portfolioForm, starting_cash: event.target.value })}
                />
              </label>
              <label>
                Cash Reserve %
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.5}
                  value={portfolioForm.cash_reserve_percent}
                  onChange={(event) => setPortfolioForm({ ...portfolioForm, cash_reserve_percent: event.target.value })}
                />
              </label>
              <label>
                Base Currency
                <select value={portfolioForm.base_currency} onChange={(event) => setPortfolioForm({ ...portfolioForm, base_currency: event.target.value })}>
                  <option value="USD">USD</option>
                </select>
              </label>
              <button className="primary-button span-2" type="submit" disabled={!canManage || submitting === "portfolio"}>
                {submitting === "portfolio" ? "Saving portfolio..." : "Save portfolio"}
              </button>
            </form>
          </Card>
        </div>

        <div className="stack-lg">
          <Card
            title={selectedDeployment ? `${selectedDeployment.strategy_name} live control` : "Deployment control"}
            subtitle="Run, pause, and monitor the currently selected paper deployment."
          >
            {!selectedDeployment ? (
              <EmptyState title="No deployment selected" description="Create the first paper deployment below, then use this panel to operate it." />
            ) : (
              <div className="stack-md">
                <div className="deployment-hero">
                  <div>
                    <p className="eyebrow">Selected Deployment</p>
                    <h3>{selectedDeployment.strategy_name}</h3>
                    <p className="card-subtitle">
                      {selectedDeployment.portfolio_name} via {selectedDeployment.broker_account_name}
                    </p>
                  </div>
                  <StatusBadge label={selectedDeployment.status} tone={statusTone(selectedDeployment.status)} />
                </div>
                <div className="summary-grid">
                  <MetricPill label="Schedule" value={selectedDeployment.schedule_expression || "n/a"} />
                  <MetricPill label="Last Run" value={formatTimestamp(selectedDeployment.last_run_at)} />
                  <MetricPill label="Next Run" value={formatTimestamp(selectedDeployment.next_run_at)} />
                  <MetricPill label="Engine" value={selectedDeployment.execution_readiness.engine_version} />
                </div>
                {selectedDeployment.last_error ? <p className="form-error">{selectedDeployment.last_error}</p> : null}
                <div className="panel-actions">
                  <button className="primary-button" onClick={() => runDeploymentAction(selectedDeployment, "run_now")} disabled={!canManage || submitting === "run_now"}>
                    Run now
                  </button>
                  <button className="ghost-button" onClick={() => runDeploymentAction(selectedDeployment, "activate")} disabled={!canManage || submitting === "activate"}>
                    Activate
                  </button>
                  <button className="ghost-button" onClick={() => runDeploymentAction(selectedDeployment, "pause")} disabled={!canManage || submitting === "pause"}>
                    Pause
                  </button>
                  <button className="ghost-button" onClick={() => runDeploymentAction(selectedDeployment, "stop")} disabled={!canManage || submitting === "stop"}>
                    Stop
                  </button>
                </div>
              </div>
            )}
          </Card>

          <Card title="Create deployment" subtitle="Link an engine-ready strategy version to a paper portfolio and start scheduling evaluations.">
            <form className="form-grid two-column" onSubmit={submitDeployment}>
              <label>
                Strategy Version
                <select
                  value={deploymentForm.strategy_version}
                  onChange={(event) => setDeploymentForm({ ...deploymentForm, strategy_version: event.target.value })}
                >
                  <option value="">Select strategy version</option>
                  {readyVersions.map((version) => (
                    <option key={version.versionId} value={version.versionId}>
                      {version.strategyName} v{version.versionNumber}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Portfolio
                <select
                  value={deploymentForm.portfolio}
                  onChange={(event) => {
                    const portfolio = portfolios.find((item) => item.id === event.target.value);
                    setDeploymentForm({
                      ...deploymentForm,
                      portfolio: event.target.value,
                      broker_account: portfolio?.broker_account ?? "",
                    });
                  }}
                >
                  <option value="">Select portfolio</option>
                  {portfolios.map((portfolio) => (
                    <option key={portfolio.id} value={portfolio.id}>
                      {portfolio.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Broker Account
                <select
                  value={deploymentForm.broker_account}
                  onChange={(event) => setDeploymentForm({ ...deploymentForm, broker_account: event.target.value })}
                >
                  <option value="">Select broker account</option>
                  {brokerAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Evaluation Schedule
                <select
                  value={deploymentForm.schedule_expression}
                  onChange={(event) => setDeploymentForm({ ...deploymentForm, schedule_expression: event.target.value })}
                >
                  {(catalog?.supported_schedules ?? ["1d"]).map((schedule) => (
                    <option key={schedule} value={schedule}>
                      {schedule}
                    </option>
                  ))}
                </select>
              </label>
              <label className="span-2">
                Initial Status
                <select value={deploymentForm.status} onChange={(event) => setDeploymentForm({ ...deploymentForm, status: event.target.value })}>
                  <option value="draft">draft</option>
                  <option value="active">active</option>
                </select>
              </label>
              <button className="primary-button span-2" type="submit" disabled={!canManage || submitting === "deployment"}>
                {submitting === "deployment" ? "Saving deployment..." : "Create deployment"}
              </button>
            </form>
          </Card>

          <section className="split-grid">
            <Card title="Portfolios" subtitle="Balances and PnL update as paper orders fill and positions are marked.">
              <div className="stack-md">
                {portfolios.length === 0 ? (
                  <EmptyState title="No portfolios" description="Create a paper portfolio to track cash, equity, reserve policy, and benchmark." />
                ) : (
                  portfolios.map((portfolio) => (
                    <div key={portfolio.id} className="entity-row">
                      <div>
                        <strong>{portfolio.name}</strong>
                        <p>
                          Cash {formatCurrency(portfolio.cash_balance)} • Equity {formatCurrency(portfolio.equity_value)}
                        </p>
                      </div>
                      <div className="entity-metrics">
                        <span className={Number(portfolio.unrealized_pnl) >= 0 ? "positive-text" : "negative-text"}>
                          {formatCurrency(portfolio.unrealized_pnl)}
                        </span>
                        <small>{formatTimestamp(portfolio.last_synced_at)}</small>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>

            <Card title="Paper accounts" subtitle="Provider wiring is isolated behind the broker adapter for future real Alpaca integration.">
              <div className="stack-md">
                {brokerAccounts.length === 0 ? (
                  <EmptyState title="No broker accounts" description="Create a paper broker account first to attach portfolios and deployments." />
                ) : (
                  brokerAccounts.map((account) => (
                    <div key={account.id} className="entity-row">
                      <div>
                        <strong>{account.name}</strong>
                        <p>
                          {account.provider_label} • {account.account_mode_label}
                        </p>
                      </div>
                      <StatusBadge label={account.is_active ? "active" : "inactive"} tone={account.is_active ? "success" : "warning"} />
                    </div>
                  ))
                )}
              </div>
            </Card>
          </section>

          <section className="split-grid">
            <Card title="Open positions" subtitle="Current marked holdings for the selected deployment portfolio.">
              {selectedPositions.length === 0 ? (
                <EmptyState title="No open positions" description="Run a deployment to create paper positions and start tracking mark-to-market exposure." />
              ) : (
                <div className="data-list">
                  {selectedPositions.map((position) => (
                    <div key={position.id} className="data-row">
                      <div>
                        <strong>{position.symbol}</strong>
                        <p>
                          Qty {formatNumber(position.quantity)} @ {formatCurrency(position.average_price)}
                        </p>
                      </div>
                      <div className="entity-metrics">
                        <span>{formatCurrency(position.market_value)}</span>
                        <strong className={Number(position.unrealized_pnl) >= 0 ? "positive-text" : "negative-text"}>
                          {formatCurrency(position.unrealized_pnl)}
                        </strong>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card title="Recent orders" subtitle="Paper orders submit and fill through the broker adapter with audit-friendly metadata.">
              {selectedOrders.length === 0 ? (
                <EmptyState title="No orders yet" description="Orders will appear here after a manual run or a scheduled evaluation produces execution intent." />
              ) : (
                <div className="data-list">
                  {selectedOrders.map((order) => (
                    <div key={order.id} className="data-row">
                      <div>
                        <strong>
                          {order.side.toUpperCase()} {order.symbol}
                        </strong>
                        <p>
                          {formatNumber(order.quantity)} shares • {order.order_type}
                        </p>
                      </div>
                      <div className="entity-metrics">
                        <StatusBadge label={order.status} tone={statusTone(order.status)} />
                        <small>{formatCurrency(order.filled_price ?? order.requested_price)}</small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </section>

          <section className="split-grid">
            <Card title="Signals" subtitle="Recent engine outputs for the selected deployment.">
              {selectedSignals.length === 0 ? (
                <EmptyState title="No signals yet" description="Signals will appear after the deployment evaluates its configured stock universe." />
              ) : (
                <div className="data-list">
                  {selectedSignals.map((signal) => (
                    <div key={signal.id} className="data-row">
                      <div>
                        <strong>{signal.symbol}</strong>
                        <p>{signal.signal_type}</p>
                      </div>
                      <div className="entity-metrics">
                        <span>{formatNumber(signal.strength)}</span>
                        <small>{formatTimestamp(signal.created_at)}</small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card title="Heartbeats" subtitle="Every scheduled or manual evaluation is persisted for operational review.">
              {selectedHeartbeats.length === 0 ? (
                <EmptyState title="No heartbeats yet" description="The first evaluation will create a heartbeat entry with summary counts and any errors." />
              ) : (
                <div className="data-list">
                  {selectedHeartbeats.map((heartbeat) => (
                    <div key={heartbeat.id} className="data-row">
                      <div>
                        <strong>{heartbeat.trigger_type}</strong>
                        <p>{formatTimestamp(heartbeat.started_at)}</p>
                      </div>
                      <div className="entity-metrics">
                        <StatusBadge label={heartbeat.status} tone={statusTone(heartbeat.status)} />
                        <small>{String(heartbeat.summary.orders_created ?? 0)} orders</small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </section>

          <Card title="Broker events" subtitle="Execution, fill, and reconciliation events for the selected deployment.">
            {selectedEvents.length === 0 ? (
              <EmptyState title="No broker events yet" description="Run a deployment to populate the event stream with order and evaluation activity." />
            ) : (
              <div className="event-feed">
                {selectedEvents.map((event) => (
                  <div key={event.id} className="event-row">
                    <div>
                      <strong>{event.message}</strong>
                      <p>{event.event_type}</p>
                    </div>
                    <small>{formatTimestamp(event.created_at)}</small>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </section>
    </div>
  );
}

function formatCurrency(value: string | number | null | undefined) {
  if (value == null) {
    return "n/a";
  }
  return `$${Number(value).toFixed(2)}`;
}

function formatNumber(value: string | number | null | undefined) {
  if (value == null) {
    return "n/a";
  }
  return Number(value).toFixed(2);
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Not yet";
  }
  return new Date(value).toLocaleString();
}

function statusTone(status: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (["active", "filled", "completed"].includes(status)) {
    return "success";
  }
  if (["paused", "draft", "pending", "running"].includes(status)) {
    return "info";
  }
  if (["stopped", "cancelled"].includes(status)) {
    return "warning";
  }
  if (["failed", "rejected"].includes(status)) {
    return "danger";
  }
  return "neutral";
}
