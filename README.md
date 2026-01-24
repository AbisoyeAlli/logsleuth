# LogSleuth

**Intelligent Log Incident Investigator** - An AI-powered agent that automatically investigates production incidents by analyzing logs in Elasticsearch.

Built for the [Elasticsearch Agent Builder Hackathon](https://elasticsearch.devpost.com/) (Jan 22 - Feb 27, 2026).

## Problem

When production incidents occur, engineers waste 30-60 minutes manually:
- Searching through thousands of log entries
- Correlating events across multiple services
- Identifying the root cause
- Finding similar past incidents

## Solution

LogSleuth is a multi-step AI agent that automates incident investigation:

1. **Intake** - Accepts error messages, alerts, or stack traces
2. **Search** - Queries Elasticsearch for relevant logs
3. **Correlate** - Traces errors across services using trace IDs
4. **Analyze** - Identifies root cause and blast radius
5. **Report** - Generates actionable summary with remediation steps

## Features

- Automated log search with time-window analysis
- Multi-service correlation via trace/request IDs
- Error frequency and pattern detection
- Root cause analysis with evidence citations
- Similar past incident matching
- Remediation suggestions

## Tech Stack

| Component | Technology |
|-----------|------------|
| Agent | Elastic Agent Builder |
| Data | Elasticsearch Cloud |
| Log Format | Elastic Common Schema (ECS) |
| Dashboard | Streamlit + Plotly |
| CLI | Python + Rich |

---

## Setup

### Prerequisites

- Python 3.9+
- Elastic Cloud account with Agent Builder access
  - **Recommended**: Elasticsearch Serverless (free trial, Agent Builder auto-enabled)
  - Or: Enterprise subscription on Elastic Cloud Hosted

### Step 1: Clone and Install

```bash
cd ~/Desktop/logsleuth
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Create Elastic Cloud Deployment

1. Go to [cloud.elastic.co/registration](https://cloud.elastic.co/registration?cta=agentbuilderhackathon)
2. Create an **Elasticsearch Serverless** project (Agent Builder is auto-enabled)
3. Note your Elasticsearch and Kibana URLs

### Step 3: Configure Credentials

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Elasticsearch
ELASTICSEARCH_URL=https://your-deployment.es.us-east-1.aws.elastic.cloud:443
ELASTICSEARCH_API_KEY=your-es-api-key

# Kibana (for Agent Builder API)
KIBANA_URL=https://your-deployment.kb.us-east-1.aws.elastic.cloud:9243
KIBANA_API_KEY=your-kibana-api-key
```

**To get API keys:**
- ES API Key: Elastic Cloud Console → Deployment → Elasticsearch → API Keys
- Kibana API Key: Kibana → Stack Management → API Keys → Create

### Step 4: Load Sample Data

```bash
# Create indices and ingest synthetic logs
python scripts/setup_elasticsearch.py

# Verify queries work
python scripts/test_queries.py
```

### Step 5: Run the Dashboard

```bash
# Start the Streamlit dashboard
cd ~/Desktop/logsleuth
source venv/bin/activate
streamlit run src/dashboard.py
```

The dashboard will open at http://localhost:8501 with:
- Real-time error monitoring
- Interactive incident investigation
- Log search interface
- Investigation history

### Step 6: Use the CLI

```bash
# Run an investigation
python -m src.cli investigate "checkout-service timeout errors"

# Search logs
python -m src.cli search --query "Connection refused" --service payment-service

# View error patterns
python -m src.cli errors --time-range 2h

# Check connection status
python -m src.cli status
```

### Step 7: Set Up Agent Builder (Optional)

See [docs/AGENT_BUILDER_SETUP.md](docs/AGENT_BUILDER_SETUP.md) for deploying to Elastic Agent Builder.

---

## Project Structure

```
logsleuth/
├── src/
│   ├── cli.py                   # Command-line interface
│   ├── dashboard.py             # Streamlit dashboard
│   ├── agent/
│   │   └── logsleuth_agent.py   # Agent configuration
│   ├── tools/                   # 6 custom investigation tools
│   │   ├── search_logs.py
│   │   ├── get_error_frequency.py
│   │   ├── find_correlated_logs.py
│   │   ├── search_past_incidents.py
│   │   └── save_investigation.py
│   ├── data/
│   │   ├── index_templates.py   # ECS index mappings
│   │   └── log_generator.py     # Synthetic log generator
│   └── utils/
│       └── elasticsearch_client.py
├── scripts/
│   ├── setup_elasticsearch.py   # One-command setup
│   ├── test_queries.py          # Query validation
│   └── deploy_agent.py          # Deploy to Agent Builder
├── docs/
│   └── AGENT_BUILDER_SETUP.md   # Agent Builder guide
├── tests/
├── .env.example
├── requirements.txt
├── DEVELOPMENT_PLAN.md
├── LICENSE                      # MIT (required for hackathon)
└── README.md
```

---

## Demo Scenario

The synthetic data includes two incident scenarios:

### Incident 1: Database Failure Cascade
- Database primary failover at T+60min
- payment-service connection pool exhaustion
- Cascades to checkout-service and api-gateway
- 89 user transactions affected

### Incident 2: Timeout Cascade
- inventory-service becomes slow under load
- Thread pool exhaustion
- Cascading timeouts across services

---

## Development

See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for the full implementation roadmap.

### Current Status: Phase 1 Complete

- [x] Project structure
- [x] Elasticsearch client configuration
- [x] ECS-compatible index templates
- [x] Synthetic log generator with incidents
- [x] Data ingestion script
- [x] Query validation tests

### Next: Phase 2 - Agent Core
- [ ] Implement Agent Builder tools
- [ ] Create LogSleuth agent
- [ ] Test investigation flow

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Resources

- [Elasticsearch Agent Builder Docs](https://www.elastic.co/docs/solutions/search/agent-builder/get-started)
- [Agent Builder API Reference](https://www.elastic.co/docs/api/doc/kibana/operation/operation-post-agent-builder-agents)
- [Free Training Course](https://www.elastic.co/training/elastic-ai-agents-mcp)
- [Hackathon Page](https://elasticsearch.devpost.com/)
