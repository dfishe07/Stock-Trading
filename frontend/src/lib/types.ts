export type Role = "admin" | "developer" | "user";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface Membership {
  id: string;
  role: Role;
  is_default: boolean;
  is_active: boolean;
  organization: Organization;
}

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  must_change_password: boolean;
  default_organization: string | null;
  memberships: Membership[];
  is_active: boolean;
  date_joined: string;
}

export interface Invitation {
  id: string;
  email: string;
  role: Role;
  status: string;
  token: string;
  organization: Organization;
  invited_by: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
}

export interface StrategyVersion {
  id: string;
  version_number: number;
  title: string;
  change_summary: string;
  definition: StrategyDefinition;
  schema_version: string;
  validation_errors: string[];
  execution_readiness: {
    is_ready: boolean;
    errors: string[];
    engine_version: string;
    supports_backtests: boolean;
    supports_live_transition: boolean;
  };
  is_published: boolean;
  created_by: string;
  created_at: string;
}

export interface Strategy {
  id: string;
  name: string;
  slug: string;
  description: string;
  status: string;
  latest_version: StrategyVersion | null;
  latest_validation_errors: string[];
  created_at: string;
  updated_at: string;
}

export interface StrategyDefinition {
  schemaVersion: string;
  metadata: {
    timeframe: string;
    schedule: {
      type: string;
      value: string;
    };
    marketSession: string;
    notes: string;
  };
  universe: {
    type: string;
    symbols: string[];
  };
  indicators: Array<{
    id: string;
    type: string;
    params: Record<string, string | number>;
  }>;
  entryRules: RuleNode;
  exitRules: RuleNode;
  sizing: {
    method: string;
    value: number;
    minCash: number;
  };
  risk: Record<string, number>;
  execution: {
    orderType: string;
    allowFractional: boolean;
    slippageBps: number;
    feesPerTrade: number;
  };
}

export type RuleNode =
  | {
      type: "group";
      operator: string;
      conditions: RuleNode[];
    }
  | {
      type: "condition";
      left: RuleOperand;
      operator: string;
      right: RuleOperand;
    };

export interface RuleOperand {
  kind: "indicator" | "literal" | "price";
  value: string | number;
}

export interface StrategyBuilderSchemaField {
  key: string;
  type: string;
  label: string;
  required?: boolean;
  options?: string[];
  placeholder?: string;
}

export interface StrategyBuilderSection {
  id: string;
  title: string;
  fields: StrategyBuilderSchemaField[];
}

export interface StrategyBuilderSchema {
  schemaVersion: string;
  supportedIndicators: Record<string, Record<string, string>>;
  supportedComparators: string[];
  supportedLogicOperators: string[];
  supportedTimeframes: string[];
  supportedSchedules: string[];
  supportedMarketSessions: string[];
  supportedPriceSources: string[];
  supportedSizingMethods: string[];
  supportedOrderTypes: string[];
  stockUniverse: StockUniverseItem[];
  sections: StrategyBuilderSection[];
}

export interface StockUniverseItem {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
}

export interface BrokerAccount {
  id: string;
  organization: string;
  name: string;
  provider: string;
  provider_label: string;
  account_mode: string;
  account_mode_label: string;
  external_account_id: string;
  credentials_reference: string;
  settings: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Portfolio {
  id: string;
  organization: string;
  broker_account: string;
  broker_account_name: string;
  name: string;
  base_currency: string;
  benchmark_symbol: string;
  starting_cash: string;
  cash_balance: string;
  equity_value: string;
  realized_pnl: string;
  unrealized_pnl: string;
  cash_reserve_percent: string;
  last_synced_at: string | null;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LiveDeployment {
  id: string;
  organization: string;
  strategy_version: string;
  strategy_name: string;
  strategy_version_number: number;
  portfolio: string;
  portfolio_name: string;
  broker_account: string;
  broker_account_name: string;
  status: string;
  schedule_expression: string;
  last_run_at: string | null;
  next_run_at: string | null;
  last_error: string;
  configuration: Record<string, unknown>;
  execution_readiness: {
    is_ready: boolean;
    errors: string[];
    engine_version: string;
    supports_backtests: boolean;
    supports_live_transition: boolean;
  };
  recent_signals: LiveSignal[];
  recent_orders: LiveOrder[];
  recent_heartbeats: LiveHeartbeat[];
  created_at: string;
  updated_at: string;
}

export interface LivePosition {
  id: string;
  portfolio: string;
  portfolio_name: string;
  symbol: string;
  quantity: string;
  average_price: string;
  last_price: string;
  market_value: string;
  realized_pnl: string;
  unrealized_pnl: string;
  opened_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LiveOrder {
  id: string;
  portfolio: string;
  portfolio_name: string;
  broker_account: string;
  deployment: string | null;
  deployment_name: string | null;
  symbol: string;
  side: string;
  quantity: string;
  order_type: string;
  requested_price: string;
  filled_price: string | null;
  status: string;
  submitted_at: string | null;
  filled_at: string | null;
  external_order_id: string;
  rejection_reason: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LiveSignal {
  id: string;
  deployment: string;
  deployment_name: string;
  symbol: string;
  signal_type: string;
  strength: string;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LiveHeartbeat {
  id: string;
  deployment: string;
  deployment_name: string;
  trigger_type: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  evaluated_symbols: string[];
  summary: Record<string, unknown>;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface BrokerEvent {
  id: string;
  broker_account: string;
  portfolio: string | null;
  portfolio_name: string | null;
  deployment: string | null;
  deployment_name: string | null;
  order: string | null;
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TradingCatalog {
  supported_schedules: string[];
  stock_universe: StockUniverseItem[];
  supported_broker_providers: string[];
  supported_account_modes: string[];
}

export interface LiveDashboardSummary {
  broker_accounts: number;
  portfolios: number;
  deployments_total: number;
  deployments_active: number;
  positions_open: number;
  orders_open: number;
  total_equity: string;
  total_cash: string;
}

export interface LiveDashboard {
  summary: LiveDashboardSummary;
  recent_events: BrokerEvent[];
  recent_heartbeats: LiveHeartbeat[];
  open_positions: LivePosition[];
  open_orders: LiveOrder[];
}

export interface BacktestMetricSnapshot {
  id: string;
  metric_type: string;
  label: string;
  value: string;
}

export interface BacktestArtifact {
  id: string;
  artifact_type: string;
  payload: Record<string, unknown>;
}

export interface BacktestTrade {
  id: string;
  symbol: string;
  entry_date: string;
  exit_date: string | null;
  entry_price: string;
  exit_price: string | null;
  quantity: string;
  gross_pnl: string;
  net_pnl: string;
  return_pct: string;
  exit_reason: string;
  metadata: Record<string, unknown>;
}

export interface BacktestRun {
  id: string;
  run_name: string;
  status: string;
  strategy_version: string;
  strategy_name: string;
  strategy_version_number: number;
  start_date: string;
  end_date: string;
  initial_cash: string;
  benchmark_symbol: string;
  universe_symbols: string[];
  run_parameters: Record<string, unknown>;
  result_summary: Record<string, number | string | string[] | null>;
  error_message: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  metrics: BacktestMetricSnapshot[];
  artifacts: BacktestArtifact[];
  trades: BacktestTrade[];
}
