# TradeGuard

**Document intelligence + risk-gated escrow for cargo trade.**

TradeGuard ingests shipping documents (bill of lading, commercial invoice, packing list, certificate of origin), classifies them, extracts key fields with OCR/NLP, cross-checks the documents against each other, and scores each shipment's risk with **XGBoost**. The risk decision controls a **payment-gateway escrow flow**: low-risk shipments auto-release funds, borderline ones go to a human reviewer, high-risk ones are held.

> Working title. Built as a portfolio project aligned with a Machine Learning Intern role in maritime/cargo document automation.

## Honest scope statement
- Training data is **synthetic** (generated documents with injected discrepancies). Metrics describe performance on that distribution, not on real-world fraud.
- Payments run in **gateway test/sandbox mode only**. No real money moves. "Escrow" is simulated with a ledger plus gateway hold/transfer features where available.
- This is a decision-support prototype, not a compliance or customs-filing system.

## Documentation index
| # | Document | Purpose |
|---|----------|---------|
| 01 | [PRD](01-PRD.md) | Problem, goals, personas, scope, success metrics, risks |
| 02 | [Features](02-FEATURES.md) | Feature list, priorities, acceptance criteria, user stories |
| 03 | [Tech stack](03-TECH-STACK.md) | Technology choices, rationale, alternatives |
| 04 | [Architecture](04-ARCHITECTURE.md) | Components, pipeline, state machine, repo layout |
| 05 | [Database schema](05-DATABASE-SCHEMA.md) | ERD and PostgreSQL DDL |
| 06 | [API spec](06-API-SPEC.md) | REST endpoints, payloads, errors |
| 07 | [ML spec](07-ML-SPEC.md) | Data generation, features, models, evaluation, model card |
| 08 | [Payment & escrow](08-PAYMENT-ESCROW.md) | Gateway flow, webhooks, ledger, failure handling |
| 09 | [Roadmap](09-ROADMAP.md) | Week-by-week plan, milestones, scope cuts |
| 10 | [Test plan](10-TEST-PLAN.md) | Testing strategy and quality gates |
| 11 | [Deployment](11-DEPLOYMENT.md) | Docker, CI/CD, AWS deployment |
| 12 | [JD alignment & portfolio](12-JD-ALIGNMENT-AND-PORTFOLIO.md) | Mapping to the internship JD, resume bullets, interview notes |

## Suggested repository layout
```
tradeguard/
├── docs/                    # this folder
├── data/                    # gitignored; generated datasets live here
├── notebooks/               # EDA, error analysis
├── src/tradeguard/
│   ├── api/                 # FastAPI routers, deps, schemas
│   ├── core/                # config, security, logging
│   ├── db/                  # models, migrations, repositories
│   ├── ocr/                 # preprocessing, OCR engines
│   ├── extraction/          # rules baseline, LayoutLM extractor
│   ├── validation/          # cross-document checks, ISO 6346
│   ├── ml/                  # datagen, features, train, evaluate, infer
│   ├── payments/            # gateway client, webhooks, ledger
│   └── services/            # shipment orchestration, decision engine
├── frontend/                # React + Vite dashboard
├── tests/
├── infra/                   # docker-compose, GitHub Actions, AWS notes
├── pyproject.toml
└── README.md
```

## Status legend used in the docs
- **P0** must have for the MVP
- **P1** should have
- **P2** stretch
