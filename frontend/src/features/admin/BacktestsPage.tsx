import { FormEvent, useEffect, useMemo, useState } from "react";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { LineChart } from "../../components/LineChart";
import { MetricPill } from "../../components/MetricPill";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch, ApiError } from "../../lib/api";
import type { BacktestRun, StockUniverseItem, Strategy } from "../../lib/types";
import { useAuth } from "../auth/AuthContext";

export function BacktestsPage() {
  const { session } = useAuth();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [universe, setUniverse] = useState<StockUniverseItem[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    strategy_version_id: "",
    run_name: "Golden Cross Daily Run",
    start_date: "2023-01-03",
    end_date: "2023-12-29",
    initial_cash: "100000.00",
    benchmark_symbol: "AAPL",
  });

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null,
    [runs, selectedRunId],
  );

  const readyStrategies = strategies.filter((strategy) => strategy.latest_version?.execution_readiness.is_ready);

  const refresh = async () => {
    if (!session) {
      return;
    }
    const [strategyPayload, runPayload, universePayload] = await Promise.all([
      apiFetch<Strategy[]>("/api/strategies/", {}, session),
      apiFetch<BacktestRun[]>("/api/backtests/runs/", {}, session),
      apiFetch<{ items: StockUniverseItem[] }>("/api/backtests/universe/", {}, session),
    ]);
    setStrategies(strategyPayload);
    setRuns(runPayload);
    setUniverse(universePayload.items);

    if (!form.strategy_version_id) {
      const firstReadyVersion = strategyPayload.find((strategy) => strategy.latest_version?.execution_readiness.is_ready)?.latest_version?.id;
      if (firstReadyVersion) {
        setForm((current) => ({ ...current, strategy_version_id: firstReadyVersion }));
      }
    }
    if (!selectedRunId && runPayload.length > 0) {
      setSelectedRunId(runPayload[0].id);
    }
  };

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load backtest data."));
  }, []);

  const submitRun = async (event: FormEvent) => {
    event.preventDefault();
    if (!session) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const run = await apiFetch<BacktestRun>(
        "/api/backtests/runs/",
        {
          method: "POST",
          body: JSON.stringify({
            ...form,
            initial_cash: Number(form.initial_cash),
          }),
        },
        session,
      );
      await refresh();
      setSelectedRunId(run.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to run backtest.");
    } finally {
      setSubmitting(false);
    }
  };

  const equityArtifact = selectedRun?.artifacts.find((artifact) => artifact.artifact_type === "equity_curve");
  const readinessArtifact = selectedRun?.artifacts.find((artifact) => artifact.artifact_type === "execution_readiness");
  const equityPoints = ((equityArtifact?.payload.points as Array<{ date: string; equity: number }>) ?? []).map((point) => ({
    date: point.date,
    equity: Number(point.equity),
  }));

  return (
    <div className="stack-xl">
      <PageHeader
        eyebrow="Backtests"
        title="Historical execution lab"
        description="Phase 2 now includes deterministic market data, backtest runs, metrics, trades, and stored artifacts so strategy versions can be evaluated before any live deployment work."
      />

      {error ? <p className="form-error">{error}</p> : null}

      <section className="split-grid">
        <Card title="Launch backtest" subtitle="Choose an engine-ready strategy version, set the date range, and persist a reproducible run.">
          <form className="form-grid two-column" onSubmit={submitRun}>
            <label className="span-2">
              Strategy Version
              <select value={form.strategy_version_id} onChange={(event) => setForm({ ...form, strategy_version_id: event.target.value })}>
                <option value="">Select a strategy version</option>
                {readyStrategies.map((strategy) =>
                  strategy.latest_version ? (
                    <option key={strategy.latest_version.id} value={strategy.latest_version.id}>
                      {strategy.name} v{strategy.latest_version.version_number}
                    </option>
                  ) : null,
                )}
              </select>
            </label>
            <label>
              Run Name
              <input value={form.run_name} onChange={(event) => setForm({ ...form, run_name: event.target.value })} />
            </label>
            <label>
              Benchmark
              <select value={form.benchmark_symbol} onChange={(event) => setForm({ ...form, benchmark_symbol: event.target.value })}>
                {universe.map((stock) => (
                  <option key={stock.symbol} value={stock.symbol}>
                    {stock.symbol}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Start Date
              <input type="date" value={form.start_date} onChange={(event) => setForm({ ...form, start_date: event.target.value })} />
            </label>
            <label>
              End Date
              <input type="date" value={form.end_date} onChange={(event) => setForm({ ...form, end_date: event.target.value })} />
            </label>
            <label className="span-2">
              Initial Cash
              <input type="number" min={1000} step={1000} value={form.initial_cash} onChange={(event) => setForm({ ...form, initial_cash: event.target.value })} />
            </label>
            <button className="primary-button span-2" type="submit" disabled={submitting || !form.strategy_version_id}>
              {submitting ? "Running backtest..." : "Run backtest"}
            </button>
          </form>
        </Card>

        <Card title="Recent runs" subtitle="Completed runs are stored with metrics, trades, and replayable artifacts.">
          <div className="stack-md">
            {runs.length === 0 ? (
              <EmptyState title="No runs yet" description="Launch the first backtest to generate metrics, trades, and an equity curve." />
            ) : (
              runs.map((run) => (
                <button
                  key={run.id}
                  className={`list-button${run.id === selectedRun?.id ? " active" : ""}`}
                  onClick={() => setSelectedRunId(run.id)}
                >
                  <span>
                    {run.run_name || run.strategy_name}
                    <small className="list-button-detail">
                      {run.strategy_name} v{run.strategy_version_number}
                    </small>
                  </span>
                  <small>{run.status}</small>
                </button>
              ))
            )}
          </div>
        </Card>
      </section>

      {selectedRun ? (
        <div className="stack-lg">
          <section className="summary-grid">
            {formatRunMetrics(selectedRun).map((metric) => (
              <MetricPill key={metric.label} label={metric.label} value={metric.value} />
            ))}
          </section>

          <LineChart title={`${selectedRun.run_name || selectedRun.strategy_name} Equity Curve`} points={equityPoints} />

          <section className="split-grid">
            <Card title="Execution Notes">
              {readinessArtifact ? (
                <div className="stack-md">
                  <strong>{String(readinessArtifact.payload.notes ?? "Engine readiness saved with the run.")}</strong>
                  <p>Engine version: {String(readinessArtifact.payload.engine_version ?? "phase2-v1")}</p>
                </div>
              ) : (
                <EmptyState title="No readiness artifact" description="Execution readiness is captured when a run completes." />
              )}
            </Card>

            <Card title="Trade Outcomes">
              {selectedRun.trades.length === 0 ? (
                <EmptyState title="No closed trades" description="This run did not open and close any positions over the selected date range." />
              ) : (
                <div className="trade-list">
                  {selectedRun.trades.slice(0, 12).map((trade) => (
                    <div key={trade.id} className="trade-row">
                      <div>
                        <strong>{trade.symbol}</strong>
                        <p>
                          {trade.entry_date} to {trade.exit_date}
                        </p>
                      </div>
                      <div className="trade-values">
                        <span>{trade.exit_reason}</span>
                        <strong className={Number(trade.net_pnl) >= 0 ? "positive-text" : "negative-text"}>
                          ${Number(trade.net_pnl).toFixed(2)}
                        </strong>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function formatRunMetrics(run: BacktestRun) {
  const summary = run.result_summary;
  return [
    { label: "Total Return", value: formatPercent(summary.total_return_pct) },
    { label: "Sharpe", value: formatNumber(summary.sharpe_ratio) },
    { label: "Max Drawdown", value: formatPercent(summary.max_drawdown_pct) },
    { label: "Win Rate", value: formatPercent(summary.win_rate_pct) },
    { label: "Trades", value: String(summary.total_trades ?? "0") },
    { label: "Ending Equity", value: formatCurrency(summary.ending_equity) },
  ];
}

function formatPercent(value: unknown) {
  return value == null ? "n/a" : `${Number(value).toFixed(2)}%`;
}

function formatCurrency(value: unknown) {
  return value == null ? "n/a" : `$${Number(value).toFixed(2)}`;
}

function formatNumber(value: unknown) {
  return value == null ? "n/a" : Number(value).toFixed(2);
}
