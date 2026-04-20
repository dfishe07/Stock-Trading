# Web Application for Algorithmic Stock Trading
## App for designing and deploying Algo trading with Alpaca API
## Code for the Strategies, algorithms preferrably written in Python


### Phase 1 MVP
Build a stable internal platform that can:
- authenticate users
- create and version Strategies (start with simple strategies such as Golden Cross but include flexibility in design to add future logic for more complex strategies)
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

## Front End
- Vite / JS.node
- Module for designing and saving new stock trading Strategies
    - Ability to save an strategy with the values to be stored in the backend / database
    - Selecting & adjusting parameters on signals (support multiple signals through AND, OR and GROUP logic)
    - Selecting & adjusting parameters on how much capital to deploy when a trade signal is met based on signal strength, other signals, risk measures, etc. 
    - Selecting & adjusting parameters for portfolio allocation and risk measures
        - Define risk controls as explicit components in strategy configuration:
            - position sizing
            - max position exposure
            - max portfolio exposure
            - stop loss rules
            - take profit rules
            - re-entry cooldowns
            - daily loss limits
            - market session constraints
    - Selecting & adjusting parameters on for stop loss, take profits, etc.
- Module for running backtests on Saved Strategy
    - Including selecting date range, portfolio / universe of stocks, etc. 
    - Ability to compare results across many differenet saved strategies
    - Ability to test sets of parameters for a given strategy
    - View and compare key metrics on performance across the backtests
    - View key events or activities that triggered more impactful results from a Strategy
    - View graphs and charts to visualize the data produced from backtesting
- Module for viewing live results of paper trading or live trading by for live Strategy
    - View key metrics on performance running live
    - View graphs and charts including indicators of where the strategy is recommending trading

## Django back-end

- Strategy respresentation
    - Represent each strategy as a versioned JSON definition plus normalized metadata.
    - Separate the user-editable strategy definition from execution records and results.
    - Use one shared execution engine for both backtests and live runs to ensure consistency.
- Treat backtesting and live trading as separate workflows built on top of the same strategy engine.
- Use separate run types, queues, data sources, and result models.
- Data architecture
    - Define a market data abstraction layer so providers can be swapped later.
    - Start with Alpaca if acceptable, but avoid hard-wiring core logic directly to Alpaca responses.
- with User login / registration
    - Include groups for user access such as "user" can't edit Algos, "developer" can edit, "admin" can do anything
    - Set up the ability to invite someone through email and they have to change their password when they login for the first time. 
    - Set up "Login As" for admins
    - Design this project to work for multiple organizations, separate books of business (portfolios), and teams for developers for example. Allow access to be given to people based on this 
- Data models to support the frontend with API calls
- Flexible data models to allow for the customization of Strategies and execution on those strategies through alpace api
- Ability to run algorithms based on schedule (if an Algo is meant to run every 15 minutes for example)
- Support for running algorithms live including
    - Pulling in live data sources to feed Strategies
    - Running the data through Strategies to develop signals, executions plans/orders, and portfolio balancing updates, etc.
    - Managing multiple portfolios live or in paper testing
- Postgres database
- Docker setup to run the application through a single terminal / server



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