import type { RuleNode, StrategyDefinition } from "../../lib/types";

const entryRule: RuleNode = {
  type: "group",
  operator: "and",
  conditions: [
    {
      type: "condition",
      left: { kind: "indicator", value: "fast_sma" },
      operator: "crosses_above",
      right: { kind: "indicator", value: "slow_sma" },
    },
  ],
};

const exitRule: RuleNode = {
  type: "group",
  operator: "or",
  conditions: [
    {
      type: "condition",
      left: { kind: "indicator", value: "fast_sma" },
      operator: "crosses_below",
      right: { kind: "indicator", value: "slow_sma" },
    },
  ],
};

export const defaultDefinition: StrategyDefinition = {
  schemaVersion: "1.0",
  metadata: {
    timeframe: "1D",
    schedule: { type: "interval", value: "1d" },
    marketSession: "regular",
    notes: "",
  },
  universe: {
    type: "symbols",
    symbols: ["AAPL", "MSFT", "JPM"],
  },
  indicators: [
    { id: "fast_sma", type: "sma", params: { period: 20, source: "close" } },
    { id: "slow_sma", type: "sma", params: { period: 50, source: "close" } },
  ],
  entryRules: entryRule,
  exitRules: exitRule,
  sizing: { method: "fixed_fraction", value: 0.1, minCash: 0 },
  risk: {
    maxPositionExposure: 0.2,
    maxPortfolioExposure: 1,
    stopLossPercent: 0.05,
    takeProfitPercent: 0.12,
    reEntryCooldownBars: 3,
    dailyLossLimitPercent: 0.03,
  },
  execution: {
    orderType: "market",
    allowFractional: false,
    slippageBps: 5,
    feesPerTrade: 0,
  },
};
