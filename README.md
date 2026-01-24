# LogSleuth

**Intelligent Log Incident Investigator** - An AI-powered agent that automatically investigates production incidents by analyzing logs in Elasticsearch.

Built for the [Elasticsearch Agent Builder Hackathon](https://elasticsearch.devpost.com/).

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

- **Agent**: Elastic Agent Builder
- **Data**: Elasticsearch Cloud
- **Log Format**: Elastic Common Schema (ECS)
- **Interface**: Python CLI

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Elasticsearch credentials

# Generate sample data
python scripts/generate_logs.py

# Run the agent
python -m src.cli investigate "checkout-service throwing timeout errors"
```

## Project Structure

```
logsleuth/
├── src/
│   ├── agent/          # Agent Builder configuration
│   ├── tools/          # Custom tools for the agent
│   ├── data/           # Data ingestion utilities
│   └── utils/          # Helper functions
├── tests/              # Test files
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── config/             # Configuration files
└── README.md
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Built for the Elasticsearch Agent Builder Hackathon 2026.
