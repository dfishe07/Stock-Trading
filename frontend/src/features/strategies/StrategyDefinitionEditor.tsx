import { Card } from "../../components/Card";
import type { RuleNode, StockUniverseItem, StrategyBuilderSchema, StrategyDefinition } from "../../lib/types";
import { StockUniversePicker } from "./StockUniversePicker";

interface StrategyDefinitionEditorProps {
  definition: StrategyDefinition;
  schema: StrategyBuilderSchema;
  onChange: (definition: StrategyDefinition) => void;
}

export function StrategyDefinitionEditor({ definition, schema, onChange }: StrategyDefinitionEditorProps) {
  const indicatorIds = definition.indicators.map((indicator) => indicator.id);
  const update = <K extends keyof StrategyDefinition>(key: K, value: StrategyDefinition[K]) => {
    onChange({ ...definition, [key]: value });
  };

  return (
    <div className="stack-lg">
      <Card title="Strategy Metadata" subtitle="Keep the high-level contract constrained so the execution engine can interpret it consistently in backtests and live workflows.">
        <div className="form-grid three-column">
          <label>
            Timeframe
            <select
              value={definition.metadata.timeframe}
              onChange={(event) =>
                update("metadata", {
                  ...definition.metadata,
                  timeframe: event.target.value,
                })
              }
            >
              {schema.supportedTimeframes.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Evaluation Schedule
            <select
              value={definition.metadata.schedule.value}
              onChange={(event) =>
                update("metadata", {
                  ...definition.metadata,
                  schedule: { ...definition.metadata.schedule, value: event.target.value },
                })
              }
            >
              {schema.supportedSchedules.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Market Session
            <select
              value={definition.metadata.marketSession}
              onChange={(event) =>
                update("metadata", {
                  ...definition.metadata,
                  marketSession: event.target.value,
                })
              }
            >
              {schema.supportedMarketSessions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="span-3">
            Notes
            <textarea
              value={definition.metadata.notes}
              onChange={(event) =>
                update("metadata", {
                  ...definition.metadata,
                  notes: event.target.value,
                })
              }
            />
          </label>
        </div>
      </Card>

      <Card title="Universe Selection" subtitle="Use the searchable stock picker to build a manageable universe from the MVP catalog of ten cross-sector symbols.">
        <StockUniversePicker
          stocks={schema.stockUniverse}
          selectedSymbols={definition.universe.symbols}
          onChange={(symbols) =>
            update("universe", {
              ...definition.universe,
              symbols,
            })
          }
        />
      </Card>

      <Card title="Indicators" subtitle="Pick from the supported indicator library and tune only the parameters the shared engine knows how to evaluate.">
        <div className="stack-md">
          {definition.indicators.map((indicator, index) => {
            const paramsForType = schema.supportedIndicators[indicator.type] ?? {};
            return (
              <div key={`${indicator.id}-${index}`} className="indicator-card">
                <div className="indicator-card-header">
                  <strong>{indicator.id || `indicator_${index + 1}`}</strong>
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() =>
                      update(
                        "indicators",
                        definition.indicators.filter((_, innerIndex) => innerIndex !== index),
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
                <div className="form-grid three-column">
                  <label>
                    Indicator ID
                    <input
                      value={indicator.id}
                      onChange={(event) => {
                        const next = structuredClone(definition);
                        next.indicators[index].id = event.target.value;
                        onChange(next);
                      }}
                    />
                  </label>
                  <label>
                    Type
                    <select
                      value={indicator.type}
                      onChange={(event) => {
                        const next = structuredClone(definition);
                        const nextType = event.target.value;
                        next.indicators[index] = {
                          id: next.indicators[index].id,
                          type: nextType,
                          params: buildDefaultParams(nextType, schema),
                        };
                        onChange(next);
                      }}
                    >
                      {Object.keys(schema.supportedIndicators).map((option) => (
                        <option key={option} value={option}>
                          {option.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </label>
                  {Object.keys(paramsForType).map((paramKey) => (
                    <label key={paramKey}>
                      {formatLabel(paramKey)}
                      {paramKey === "source" ? (
                        <select
                          value={String(indicator.params[paramKey])}
                          onChange={(event) => {
                            const next = structuredClone(definition);
                            next.indicators[index].params[paramKey] = event.target.value;
                            onChange(next);
                          }}
                        >
                          {schema.supportedPriceSources.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="number"
                          min={1}
                          value={String(indicator.params[paramKey])}
                          onChange={(event) => {
                            const next = structuredClone(definition);
                            next.indicators[index].params[paramKey] = Number(event.target.value);
                            onChange(next);
                          }}
                        />
                      )}
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
          <button
            type="button"
            className="primary-button"
            onClick={() =>
              update("indicators", [
                ...definition.indicators,
                {
                  id: `indicator_${definition.indicators.length + 1}`,
                  type: "sma",
                  params: buildDefaultParams("sma", schema),
                },
              ])
            }
          >
            Add indicator
          </button>
        </div>
      </Card>

      <RuleGroupCard
        title="Entry Rules"
        node={definition.entryRules}
        indicatorIds={indicatorIds}
        priceSources={schema.supportedPriceSources}
        schema={schema}
        onChange={(node) => update("entryRules", node)}
      />

      <RuleGroupCard
        title="Exit Rules"
        node={definition.exitRules}
        indicatorIds={indicatorIds}
        priceSources={schema.supportedPriceSources}
        schema={schema}
        onChange={(node) => update("exitRules", node)}
      />

      <Card title="Execution Controls" subtitle="Use explicit picklists for fields that map directly to execution semantics.">
        <div className="form-grid three-column">
          <label>
            Sizing Method
            <select
              value={definition.sizing.method}
              onChange={(event) =>
                update("sizing", {
                  ...definition.sizing,
                  method: event.target.value,
                })
              }
            >
              {schema.supportedSizingMethods.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Target Allocation
            <input
              type="number"
              step="0.01"
              value={definition.sizing.value}
              onChange={(event) =>
                update("sizing", {
                  ...definition.sizing,
                  value: Number(event.target.value),
                })
              }
            />
          </label>
          <label>
            Minimum Cash Buffer
            <input
              type="number"
              step="100"
              value={definition.sizing.minCash}
              onChange={(event) =>
                update("sizing", {
                  ...definition.sizing,
                  minCash: Number(event.target.value),
                })
              }
            />
          </label>
          <label>
            Order Type
            <select
              value={definition.execution.orderType}
              onChange={(event) =>
                update("execution", {
                  ...definition.execution,
                  orderType: event.target.value,
                })
              }
            >
              {schema.supportedOrderTypes.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label>
            Slippage (bps)
            <input
              type="number"
              value={definition.execution.slippageBps}
              onChange={(event) =>
                update("execution", {
                  ...definition.execution,
                  slippageBps: Number(event.target.value),
                })
              }
            />
          </label>
          <label className="toggle-field">
            <span>Allow Fractional Shares</span>
            <input
              type="checkbox"
              checked={definition.execution.allowFractional}
              onChange={(event) =>
                update("execution", {
                  ...definition.execution,
                  allowFractional: event.target.checked,
                })
              }
            />
          </label>
        </div>
      </Card>

      <Card title="Risk Controls" subtitle="The backend persists these controls explicitly so later live execution can reuse the same safety envelope.">
        <div className="form-grid three-column">
          {Object.entries(definition.risk).map(([key, value]) => (
            <label key={key}>
              {formatLabel(key)}
              <input
                type="number"
                step={key === "reEntryCooldownBars" ? "1" : "0.01"}
                min="0"
                value={value}
                onChange={(event) =>
                  update("risk", {
                    ...definition.risk,
                    [key]: Number(event.target.value),
                  })
                }
              />
            </label>
          ))}
        </div>
      </Card>
    </div>
  );
}

function RuleGroupCard({
  title,
  node,
  indicatorIds,
  priceSources,
  schema,
  onChange,
}: {
  title: string;
  node: RuleNode;
  indicatorIds: string[];
  priceSources: string[];
  schema: StrategyBuilderSchema;
  onChange: (node: RuleNode) => void;
}) {
  if (node.type !== "group") {
    return null;
  }

  return (
    <Card title={title} subtitle="Build grouped rule logic using typed operands instead of free-form expression text.">
      <div className="stack-md">
        <label>
          Group Operator
          <select value={node.operator} onChange={(event) => onChange({ ...node, operator: event.target.value })}>
            {schema.supportedLogicOperators.map((option) => (
              <option key={option} value={option}>
                {option.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
        {node.conditions.map((condition, index) => (
          <ConditionEditor
            key={index}
            condition={condition}
            indicatorIds={indicatorIds}
            priceSources={priceSources}
            schema={schema}
            onChange={(nextCondition) =>
              onChange({
                ...node,
                conditions: node.conditions.map((existing, innerIndex) => (innerIndex === index ? nextCondition : existing)),
              })
            }
            onRemove={() =>
              onChange({
                ...node,
                conditions: node.conditions.filter((_, innerIndex) => innerIndex !== index),
              })
            }
          />
        ))}
        <button
          type="button"
          className="ghost-button"
          onClick={() =>
            onChange({
              ...node,
              conditions: [...node.conditions, defaultCondition(indicatorIds)],
            })
          }
        >
          Add condition
        </button>
      </div>
    </Card>
  );
}

function ConditionEditor({
  condition,
  indicatorIds,
  priceSources,
  schema,
  onChange,
  onRemove,
}: {
  condition: RuleNode;
  indicatorIds: string[];
  priceSources: string[];
  schema: StrategyBuilderSchema;
  onChange: (node: RuleNode) => void;
  onRemove: () => void;
}) {
  if (condition.type !== "condition") {
    return null;
  }

  return (
    <div className="condition-card">
      <div className="condition-grid">
        <OperandEditor
          title="Left"
          operand={condition.left}
          indicatorIds={indicatorIds}
          priceSources={priceSources}
          onChange={(operand) => onChange({ ...condition, left: operand })}
        />
        <label>
          Comparator
          <select value={condition.operator} onChange={(event) => onChange({ ...condition, operator: event.target.value })}>
            {schema.supportedComparators.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <OperandEditor
          title="Right"
          operand={condition.right}
          indicatorIds={indicatorIds}
          priceSources={priceSources}
          onChange={(operand) => onChange({ ...condition, right: operand })}
        />
      </div>
      <button type="button" className="ghost-button" onClick={onRemove}>
        Remove condition
      </button>
    </div>
  );
}

function OperandEditor({
  title,
  operand,
  indicatorIds,
  priceSources,
  onChange,
}: {
  title: string;
  operand: { kind: "indicator" | "literal" | "price"; value: string | number };
  indicatorIds: string[];
  priceSources: string[];
  onChange: (operand: { kind: "indicator" | "literal" | "price"; value: string | number }) => void;
}) {
  return (
    <label>
      {title}
      <div className="operand-editor">
        <select
          value={operand.kind}
          onChange={(event) => {
            const nextKind = event.target.value as "indicator" | "literal" | "price";
            onChange({
              kind: nextKind,
              value: nextKind === "literal" ? 50 : nextKind === "price" ? priceSources[0] ?? "close" : indicatorIds[0] ?? "fast_sma",
            });
          }}
        >
          <option value="indicator">indicator</option>
          <option value="price">price</option>
          <option value="literal">literal</option>
        </select>
        {operand.kind === "literal" ? (
          <input type="number" value={Number(operand.value)} onChange={(event) => onChange({ ...operand, value: Number(event.target.value) })} />
        ) : operand.kind === "price" ? (
          <select value={String(operand.value)} onChange={(event) => onChange({ ...operand, value: event.target.value })}>
            {priceSources.map((source) => (
              <option key={source} value={source}>
                {source}
              </option>
            ))}
          </select>
        ) : (
          <select value={String(operand.value)} onChange={(event) => onChange({ ...operand, value: event.target.value })}>
            {indicatorIds.map((indicatorId) => (
              <option key={indicatorId} value={indicatorId}>
                {indicatorId}
              </option>
            ))}
          </select>
        )}
      </div>
    </label>
  );
}

function defaultCondition(indicatorIds: string[]): RuleNode {
  return {
    type: "condition",
    left: { kind: "indicator", value: indicatorIds[0] ?? "fast_sma" },
    operator: "gt",
    right: { kind: "price", value: "close" },
  };
}

function buildDefaultParams(indicatorType: string, schema: StrategyBuilderSchema) {
  return Object.fromEntries(
    Object.entries(schema.supportedIndicators[indicatorType]).map(([key, type]) => {
      if (key === "source") {
        return [key, schema.supportedPriceSources[0]];
      }
      return [key, type === "integer" ? 14 : ""];
    }),
  );
}

function formatLabel(value: string) {
  return value
    .replace(/([A-Z])/g, " $1")
    .replace(/_/g, " ")
    .replace(/^./, (character) => character.toUpperCase());
}
