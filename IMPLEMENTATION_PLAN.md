# Algorithmic Stock Trading Application Plan

## Purpose
This document translates the current README into a practical implementation plan and highlights the major design decisions that should be settled before development begins.

## High-Level Design Gaps In The Current README

### 1. Strategy representation is underspecified
The README describes a flexible strategy builder, but it does not define how a strategy is stored or executed. This is the most important gap in the project.

Without a clear strategy definition, the team cannot reliably:
- save strategies in the database
- validate them in the UI or API
- execute them in backtests and live trading the same way
- version strategies over time
- explain why a trade was generated

Recommendation:
- Represent each strategy as a versioned JSON definition plus normalized metadata.
- Separate the user-editable strategy definition from execution records and results.
- Use one shared execution engine for both backtests and live runs.

### 2. Backtesting and live trading are mixed conceptually
The README correctly asks for both backtesting and live execution, but it does not separate their operational requirements.

These are different systems:
- Backtesting is batch, historical, reproducible, and compute-heavy.
- Live trading is event-driven, stateful, failure-sensitive, and time-sensitive.

Recommendation:
- Treat backtesting and live trading as separate workflows built on top of the same strategy engine.
- Use separate run types, queues, data sources, and result models.

### 3. No explicit market data architecture
The README mentions Alpaca, but Alpaca alone does not answer all data requirements.

Unclear items include:
- historical bars source
- real-time quotes/bars source
- corporate actions handling
- symbol universe management
- time zone and trading calendar rules
- data retention policy

Recommendation:
- Define a market data abstraction layer so providers can be swapped later.
- Start with Alpaca if acceptable, but avoid hard-wiring core logic directly to Alpaca responses.

### 4. Scheduling and background execution are not designed
Running strategies every 15 minutes or continuously requires background workers, job orchestration, retries, and auditability.

Recommendation:
- Use Django for the API and admin layer.
- Use a task runner and scheduler for asynchronous work.
- Suggested stack: Django + Django REST Framework + Celery + Redis + Postgres.

### 5. Multi-tenant portfolio ownership is unclear
The README mentions multiple portfolios and user roles, but it does not define ownership boundaries.

Open concerns:
- Can users see only their own portfolios and strategies?
- Can developers edit global strategy templates or only their own?
- Are portfolios linked to one brokerage account or many?
- Are paper and live accounts separate entities?

Recommendation:
- Model ownership explicitly with `organization`, `user`, `portfolio`, and `broker_account` boundaries.
- Decide early whether the app is single-tenant for one team or multi-tenant for many customers.

### 6. Risk management and order controls need first-class design
The README mentions stop loss, take profit, and capital deployment, but these should not be ad hoc parameters attached loosely to strategies.

Recommendation:
- Define risk controls as explicit components in strategy configuration:
  - position sizing
  - max position exposure
  - max portfolio exposure
  - stop loss rules
  - take profit rules
  - re-entry cooldowns
  - daily loss limits
  - market session constraints

### 7. Audit, observability, and compliance concerns are missing
A trading platform needs strong traceability even if it starts as an internal tool.

Recommendation:
- Log every strategy version, run, signal, order intent, broker response, and state change.
- Build immutable audit records for live execution.
- Store enough context to explain every trade after the fact.

### 8. The frontend scope is too broad for an initial build
The README includes a strategy builder, backtests, comparison tools, live dashboards, visualizations, auth, invitations, and role controls.

Recommendation:
- Define an MVP with one strategy type, one data source, one broker integration, one portfolio model, and one backtest flow.
- Add advanced comparison, parameter sweeps, and rich analytics in later phases.

## Recommended Product Scope

### Phase 1 MVP
Build a stable internal platform that can:
- authenticate users
- create and version Strategies
- run historical backtests
- display results
- connect one Alpaca paper account
- run scheduled paper trading
- show live positions, orders, and recent signals

Do not include in the first phase:
- live-money trading
- broad no-code strategy flexibility without guardrails
- multi-broker support
- highly custom indicator scripting by end users
- advanced optimization grids across huge parameter spaces
- cross-tenant enterprise features

## Recommended Architecture

### Frontend
- Vite + React + TypeScript
- Component-based strategy builder with schema-driven forms
- Charting for backtest and live results
- Separate views for:
  - strategy management
  - backtest runs
  - live portfolios
  - admin / user management

### Backend
- Django
- Django REST Framework
- Postgres
- Celery workers
- Redis for task queue / caching
- Django admin for operational support

### Core backend services
- Auth and user management service
- Strategy definition and validation service
- Market data service
- Backtest engine service
- Live execution service
- Portfolio and risk service
- Broker integration service
- Notification and audit service

## Recommended Domain Model

### Identity and access
- `User`
- `Organization` if multi-user team ownership is required
- `RoleMembership`
- `Invitation`

### Strategy management
- `Strategy`
- `StrategyVersion`
- `StrategyParameterSet`
- `StrategyRun`
- `SignalEvent`
- `ExecutionDecision`

### Trading and portfolios
- `BrokerAccount`
- `Portfolio`
- `Position`
- `Order`
- `Fill`
- `CashLedger`

### Backtesting
- `BacktestRun`
- `BacktestTrade`
- `BacktestMetricSnapshot`
- `BacktestArtifact`

### Live operations
- `LiveDeployment`
- `LiveHeartbeat`
- `LiveSignal`
- `LiveOrderIntent`
- `BrokerEvent`

## Strategy System Recommendation

### Use a structured strategy definition, not arbitrary Python entered by users
Allowing users to directly author Python strategy code too early creates major risks:
- security issues
- unstable runtime behavior
- poor validation
- hard-to-debug failures
- weak UI support

Recommendation:
- Start with a declarative strategy schema.
- Support a controlled library of indicators, conditions, operators, and risk rules.
- Keep developer-authored Python for engine internals and custom extensions only.

### Example strategy model
A strategy version should define:
- universe selection
- timeframe
- entry rules
- exit rules
- sizing rules
- portfolio constraints
- execution constraints
- schedule
- slippage and fee assumptions for backtests

This gives the frontend a stable contract and keeps the execution engine deterministic.

## Execution Model Recommendation

### Backtest flow
1. User selects a saved strategy version and parameters.
2. Backend creates a `BacktestRun`.
3. Worker loads historical data and simulates execution.
4. Results, metrics, charts, and event logs are stored as artifacts.

### Live flow
1. User deploys a strategy version to a paper account.
2. Scheduler or stream listener triggers evaluation.
3. Engine produces signals and order intents.
4. Risk checks validate exposure and trading rules.
5. Broker integration submits orders.
6. Broker responses update positions, orders, and audit records.

## Security And Access Control

### Recommended permission model
- `admin`: full access including user management, impersonation, operational controls
- `developer`: can create and edit strategies, run backtests, manage paper deployments
- `user`: can view allowed portfolios, run permitted backtests, and monitor live results

### Special considerations
- Admin impersonation should be tightly audited.
- Invitation flows should use one-time tokens and forced password reset.
- API permissions must enforce object-level access, not only UI-level restrictions.

## Infrastructure And Deployment

### Recommended local and server setup
- Docker Compose for local development
- Separate containers for:
  - frontend
  - django api
  - celery worker
  - celery beat or scheduler
  - postgres
  - redis

### Environment separation
- local
- staging
- production

Paper trading should be fully validated in staging before any live trading support is considered.

## Implementation Phases

### Phase 0: Architecture and contracts
- Finalize MVP scope
- Define tenancy model
- Define strategy JSON schema
- Define core database entities
- Define provider abstraction for market data and broker APIs
- Establish deployment and secrets strategy

### Phase 1: Platform foundation
- Set up Django, DRF, Postgres, Redis, Celery
- Set up React frontend with auth shell
- Implement user registration, invitations, role-based access
- Implement strategy CRUD and versioning
- Add basic admin tools

### Phase 2: Backtesting
- Build historical market data ingestion and normalization
- Implement strategy validation and execution engine
- Implement backtest runs and result storage
- Build UI for launching and reviewing backtests
- Add key metrics and charts

### Phase 3: Paper trading
- Add Alpaca paper broker integration
- Build scheduled and event-driven strategy evaluation
- Add order submission, reconciliation, and portfolio state tracking
- Build live dashboard for positions, orders, signals, and PnL

### Phase 4: Safety and operations
- Add audit logs, alerting, retries, and health monitoring
- Add risk guardrails and kill switches
- Add deployment controls and operational dashboards

### Phase 5: Advanced features
- Strategy comparison across runs
- Parameter sweeps and optimization jobs
- Rich event annotations and explainability views
- Multi-broker or multi-data-provider support
- Live-money trading, only after paper trading proves stable

## Recommended Initial Deliverables

Before writing production code, produce these documents first:
- product requirements document for MVP
- architecture decision record for strategy representation
- architecture decision record for multi-tenant vs single-tenant ownership
- API contract draft for strategy CRUD and backtests
- initial database schema draft
- deployment diagram

## Immediate Next Steps
1. Decide whether this application is single-tenant or multi-tenant.
2. Decide whether end users can only configure predefined strategy building blocks or can author custom code.
3. Freeze an MVP that supports paper trading only.
4. Design the strategy schema and execution contract before building the UI.
5. Build backtesting first, then paper trading, then live trading.

## Recommendation Summary
The most important design decision is to treat strategy definitions as structured, versioned configurations executed by a shared engine. If that is defined well, the frontend builder, backtesting, paper trading, scheduling, and audit model all become much easier to implement consistently.
