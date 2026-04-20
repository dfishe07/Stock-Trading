import { FormEvent, useEffect, useMemo, useState } from "react";
import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { MetricPill } from "../../components/MetricPill";
import { PageHeader } from "../../components/PageHeader";
import { apiFetch, ApiError } from "../../lib/api";
import type { Strategy, StrategyBuilderSchema, StrategyDefinition, StrategyVersion } from "../../lib/types";
import { useAuth } from "../auth/AuthContext";
import { defaultDefinition } from "./defaults";
import { StrategyDefinitionEditor } from "./StrategyDefinitionEditor";

export function StrategiesPage() {
  const { session } = useAuth();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [versions, setVersions] = useState<StrategyVersion[]>([]);
  const [schema, setSchema] = useState<StrategyBuilderSchema | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("Golden Cross");
  const [draftDescription, setDraftDescription] = useState("Baseline moving-average crossover strategy for internal validation.");
  const [draftDefinition, setDraftDefinition] = useState<StrategyDefinition>(defaultDefinition);
  const [changeSummary, setChangeSummary] = useState("Initial version");
  const [error, setError] = useState<string | null>(null);

  const selectedStrategy = useMemo(
    () => strategies.find((strategy) => strategy.id === selectedId) ?? null,
    [selectedId, strategies],
  );
  const readiness = selectedStrategy?.latest_version?.execution_readiness;

  const refresh = async () => {
    if (!session) {
      return;
    }
    const [strategyPayload, schemaPayload] = await Promise.all([
      apiFetch<Strategy[]>("/api/strategies/", {}, session),
      apiFetch<StrategyBuilderSchema>("/api/strategies/schema/", {}, session),
    ]);
    setStrategies(strategyPayload);
    setSchema(schemaPayload);
    if (!selectedId && strategyPayload.length > 0) {
      setSelectedId(strategyPayload[0].id);
    }
  };

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load strategies."));
  }, []);

  useEffect(() => {
    if (!selectedStrategy?.latest_version) {
      return;
    }
    setDraftName(selectedStrategy.name);
    setDraftDescription(selectedStrategy.description);
    setDraftDefinition(selectedStrategy.latest_version.definition);
    setChangeSummary(`Refine ${selectedStrategy.name}`);
  }, [selectedStrategy]);

  useEffect(() => {
    if (!session || !selectedStrategy) {
      setVersions([]);
      return;
    }
    apiFetch<StrategyVersion[]>(`/api/strategies/${selectedStrategy.id}/versions/`, {}, session)
      .then(setVersions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Unable to load strategy versions."));
  }, [selectedStrategy?.id, session?.token]);

  const saveNewStrategy = async (event: FormEvent) => {
    event.preventDefault();
    if (!session) {
      return;
    }
    setError(null);
    try {
      await apiFetch(
        "/api/strategies/",
        {
          method: "POST",
          body: JSON.stringify({
            name: draftName,
            description: draftDescription,
            change_summary: changeSummary,
            definition: draftDefinition,
          }),
        },
        session,
      );
      setDraftName("Golden Cross");
      setDraftDescription("Baseline moving-average crossover strategy for internal validation.");
      setDraftDefinition(defaultDefinition);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save strategy.");
    }
  };

  const saveNewVersion = async () => {
    if (!session || !selectedStrategy) {
      return;
    }
    setError(null);
    try {
      await apiFetch(
        `/api/strategies/${selectedStrategy.id}/`,
        {
          method: "PATCH",
          body: JSON.stringify({
            name: draftName,
            description: draftDescription,
            status: selectedStrategy.status,
          }),
        },
        session,
      );
      await apiFetch(
        `/api/strategies/${selectedStrategy.id}/versions/`,
        {
          method: "POST",
          body: JSON.stringify({
            title: `Version ${Date.now()}`,
            change_summary: changeSummary,
            definition: draftDefinition,
          }),
        },
        session,
      );
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create strategy version.");
    }
  };

  const publishVersion = async (version: StrategyVersion) => {
    if (!session || !selectedStrategy) {
      return;
    }
    await apiFetch(`/api/strategies/${selectedStrategy.id}/publish/${version.id}/`, { method: "POST" }, session);
    await refresh();
  };

  if (!schema) {
    return <div className="loading-state">Loading strategy workspace.</div>;
  }

  return (
    <div className="stack-xl">
      <PageHeader
        eyebrow="Strategy Management"
        title="Versioned strategy workspace"
        description="Phase 2 adds a builder that stays inside the execution contract: searchable universe selection, structured indicators, rule composition, and backtest-ready validation."
      />

      {error ? <p className="form-error">{error}</p> : null}

      <section className="summary-grid">
        <MetricPill label="Strategies" value={String(strategies.length)} />
        <MetricPill label="Universe Size" value={String(draftDefinition.universe.symbols.length)} />
        <MetricPill label="Indicators" value={String(draftDefinition.indicators.length)} />
        <MetricPill label="Backtest Ready" value={readiness?.is_ready ? "Yes" : "Needs review"} />
      </section>

      <section className="layout-grid">
        <Card title="Saved strategies" subtitle="Select a strategy to review its latest definition or create a fresh strategy from the template.">
          <div className="stack-md">
            {strategies.length === 0 ? (
              <EmptyState
                title="No strategies yet"
                description="Create the first strategy now. Versioning will begin automatically with the initial definition."
              />
            ) : (
              strategies.map((strategy) => (
                <button
                  key={strategy.id}
                  className={`list-button${strategy.id === selectedId ? " active" : ""}`}
                  onClick={() => setSelectedId(strategy.id)}
                >
                  <span>
                    {strategy.name}
                    <small className="list-button-detail">
                      {strategy.latest_version?.execution_readiness.is_ready ? "Engine ready" : "Validation needed"}
                    </small>
                  </span>
                  <small>{strategy.status}</small>
                </button>
              ))
            )}
          </div>
        </Card>

        <div className="stack-lg">
          <Card title={selectedStrategy ? `Edit ${selectedStrategy.name}` : "Create a strategy"} subtitle="Metadata changes are saved directly; strategy logic is always versioned as a new immutable definition.">
            <form className="form-grid two-column" onSubmit={saveNewStrategy}>
              <label>
                Name
                <input value={draftName} onChange={(event) => setDraftName(event.target.value)} />
              </label>
              <label>
                Change summary
                <input value={changeSummary} onChange={(event) => setChangeSummary(event.target.value)} />
              </label>
              <label className="span-2">
                Description
                <textarea value={draftDescription} onChange={(event) => setDraftDescription(event.target.value)} />
              </label>
              {selectedStrategy ? (
                <button className="primary-button span-2" type="button" onClick={saveNewVersion}>
                  Save new version
                </button>
              ) : (
                <button className="primary-button span-2" type="submit">
                  Create strategy
                </button>
              )}
            </form>
          </Card>

          <StrategyDefinitionEditor definition={draftDefinition} schema={schema} onChange={setDraftDefinition} />

          <Card title="Execution Readiness" subtitle="The strategy must stay inside the supported operator and indicator set so the shared engine can run it consistently.">
            {readiness?.is_ready ? (
              <div className="success-panel">
                <strong>Ready for backtesting and live transition scaffolding.</strong>
                <p>Engine version: {readiness.engine_version}</p>
              </div>
            ) : (
              <div className="warning-block">
                {(readiness?.errors ?? ["Save the strategy to validate it."]).map((message) => (
                  <p key={message}>{message}</p>
                ))}
              </div>
            )}
          </Card>

          <Card title="Version history">
            {selectedStrategy?.latest_version ? (
              <div className="stack-md">
                {selectedStrategy.latest_validation_errors.length > 0 ? (
                  <div className="warning-block">
                    {selectedStrategy.latest_validation_errors.map((message) => (
                      <p key={message}>{message}</p>
                    ))}
                  </div>
                ) : null}
                {versions.map((version) => (
                  <div key={version.id} className="version-row">
                    <div>
                      <strong>v{version.version_number}</strong>
                      <p>{version.change_summary || "No summary provided."}</p>
                      <small className="muted-inline">
                        {version.execution_readiness.is_ready ? "Execution-ready" : "Needs validation"}
                      </small>
                    </div>
                    <button className="ghost-button" onClick={() => publishVersion(version)}>
                      {version.is_published ? "Published" : "Publish"}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No version selected" description="Create a strategy or select an existing one to inspect version history." />
            )}
          </Card>
        </div>
      </section>
    </div>
  );
}
