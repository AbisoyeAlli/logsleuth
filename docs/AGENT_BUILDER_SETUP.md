# Elastic Agent Builder Setup Guide

This guide walks you through setting up Elastic Agent Builder for the LogSleuth project.

## Prerequisites

You need one of the following Elastic subscriptions:
- **Elastic Cloud Hosted**: Enterprise subscription
- **Elasticsearch Serverless**: Complete feature tier (easiest for hackathon)
- **Security Serverless**: Security Analytics Complete

> **Recommendation for Hackathon**: Use **Elasticsearch Serverless** - Agent Builder is enabled automatically and you get a free trial.

---

## Step 1: Create an Elastic Cloud Account

1. Go to [cloud.elastic.co/registration](https://cloud.elastic.co/registration?cta=agentbuilderhackathon)
2. Sign up for a free trial
3. Choose **Elasticsearch Serverless** project type (Agent Builder is auto-enabled)

---

## Step 2: Get Your Credentials

### Elasticsearch URL & API Key

1. In Elastic Cloud console, go to your deployment
2. Click on **Elasticsearch**
3. Copy the **Endpoint URL**
4. Go to **API Keys** → Create a new key
5. Copy the encoded API key

### Kibana URL & API Key

1. In Elastic Cloud console, click on **Kibana**
2. Copy the **Endpoint URL**
3. Open Kibana in browser
4. Go to **Stack Management** → **API Keys**
5. Click **Create API key** → name it `logsleuth`
6. Copy the encoded key

### Update your .env file

```bash
cd ~/Desktop/logsleuth
cp .env.example .env
```

Edit `.env` with your credentials:
```
ELASTICSEARCH_URL=https://your-deployment.es.us-east-1.aws.elastic.cloud:443
ELASTICSEARCH_API_KEY=your-es-api-key

KIBANA_URL=https://your-deployment.kb.us-east-1.aws.elastic.cloud:9243
KIBANA_API_KEY=your-kibana-api-key
```

---

## Step 3: Verify Agent Builder is Enabled

1. Open Kibana in your browser
2. Look for **Agents** in the left navigation menu (or search "Agents" in global search)
3. You should see the Agent Builder interface

If you don't see it:
- Ensure you're using Elasticsearch Serverless, OR
- Go to **Stack Management** → **Spaces** and switch to Elasticsearch solution navigation

---

## Step 4: Test the Default Agent

1. Click on **Agents** in Kibana
2. Open the **Agent Chat** interface
3. The default "Elastic AI Agent" should be available
4. Try asking: "What indices are available?"

---

## Step 5: Understanding Agent Builder Components

### Tools
Tools are reusable skills that agents can use. They wrap:
- **ES|QL queries** - for searching and analyzing data
- **Search queries** - for retrieving documents
- **Workflows** - for complex multi-step operations

### Agents
Agents combine:
- **System instructions** - defining persona and behavior
- **Assigned tools** - what capabilities the agent has
- **LLM configuration** - which model to use (default: Elastic Managed LLM)

### How They Work Together
```
User Query → Agent → Selects Tool(s) → Executes Query → Synthesizes Response
```

---

## Step 6: Create Your First Tool (UI Method)

Let's create a simple tool to test the workflow:

1. Go to **Agents** → **Tools** → **New tool**
2. Fill in:
   - **Tool ID**: `search_error_logs`
   - **Description**: "Search for error logs in the logs-logsleuth index. Use this when the user asks about errors or incidents."
   - **Labels**: `retrieval`, `logs`
3. Select **ES|QL** as the tool type
4. Enter query:
   ```esql
   FROM logs-logsleuth
   | WHERE log.level == "error"
   | WHERE @timestamp >= NOW() - ?time_range
   | STATS count = COUNT(*) BY service.name, error.type
   | SORT count DESC
   | LIMIT 20
   ```
5. Click **Infer parameters from query** (this detects `?time_range`)
6. Configure the parameter:
   - Name: `time_range`
   - Type: `string`
   - Description: "Time range to search, e.g., '1h', '30m', '1d'"
   - Required: Yes
7. Click **Save & Test**

---

## Step 7: Create Your First Tool (API Method)

Alternatively, create tools via API:

```bash
curl -X POST "${KIBANA_URL}/api/agent_builder/tools" \
  -H "Authorization: ApiKey ${KIBANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "kbn-xsrf: true" \
  -d '{
    "toolId": "search_error_logs",
    "description": "Search for error logs. Use when user asks about errors or incidents.",
    "labels": ["retrieval", "logs"],
    "type": "esql",
    "configuration": {
      "query": "FROM logs-logsleuth | WHERE log.level == \"error\" | WHERE @timestamp >= NOW() - ?time_range | STATS count = COUNT(*) BY service.name, error.type | SORT count DESC | LIMIT 20"
    },
    "parameters": [
      {
        "name": "time_range",
        "type": "string",
        "description": "Time range to search (e.g., 1h, 30m, 1d)",
        "required": true
      }
    ]
  }'
```

---

## Step 8: Create a Custom Agent (UI Method)

1. Go to **Agents** → **New agent**
2. Fill in:
   - **Agent ID**: `logsleuth`
   - **Display name**: `LogSleuth - Incident Investigator`
3. Enter system instructions:
   ```
   You are LogSleuth, an expert incident investigator for DevOps and SRE teams.

   Your role is to analyze logs, identify root causes of incidents, and provide
   actionable insights. When investigating an incident:

   1. UNDERSTAND: Clarify the problem and time range
   2. SEARCH: Use available tools to find relevant logs
   3. CORRELATE: Look for patterns across services using trace IDs
   4. ANALYZE: Identify the root cause and affected services
   5. REPORT: Provide a clear summary with timeline and recommendations

   Always be specific about timestamps, error counts, and affected services.
   Use markdown tables for clarity when presenting data.
   ```
4. Under **Tools**, select the tools you want this agent to use
5. Click **Save**

---

## Step 9: Create a Custom Agent (API Method)

```bash
curl -X POST "${KIBANA_URL}/api/agent_builder/agents" \
  -H "Authorization: ApiKey ${KIBANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "kbn-xsrf: true" \
  -d '{
    "agentId": "logsleuth",
    "name": "LogSleuth - Incident Investigator",
    "instructions": "You are LogSleuth, an expert incident investigator...",
    "tools": ["search_error_logs"]
  }'
```

---

## Step 10: Test Your Agent

1. Go to **Agent Chat**
2. Select your `LogSleuth` agent from the dropdown
3. Try: "What errors occurred in the last hour?"
4. The agent should use your tool and return results

---

## API Reference

### List all tools
```bash
curl -X GET "${KIBANA_URL}/api/agent_builder/tools" \
  -H "Authorization: ApiKey ${KIBANA_API_KEY}"
```

### List all agents
```bash
curl -X GET "${KIBANA_URL}/api/agent_builder/agents" \
  -H "Authorization: ApiKey ${KIBANA_API_KEY}"
```

### Chat with an agent
```bash
curl -X POST "${KIBANA_URL}/api/agent_builder/converse" \
  -H "Authorization: ApiKey ${KIBANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "kbn-xsrf: true" \
  -d '{
    "agentId": "logsleuth",
    "message": "What errors occurred in the last hour?"
  }'
```

### Execute a tool directly
```bash
curl -X POST "${KIBANA_URL}/api/agent_builder/tools/execute" \
  -H "Authorization: ApiKey ${KIBANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "kbn-xsrf: true" \
  -d '{
    "toolId": "search_error_logs",
    "parameters": {
      "time_range": "1h"
    }
  }'
```

---

## Troubleshooting

### "Agent Builder not found"
- Ensure you're on Elasticsearch Serverless or have Enterprise subscription
- Check that you're in the Elasticsearch solution view, not classic Kibana

### "Unauthorized" errors
- Regenerate your API key with correct permissions
- Ensure the key has `manage_agent_builder` and `read_agent_builder` privileges

### "Index not found" in tools
- Run `python scripts/setup_elasticsearch.py` first to create and populate indices

---

## Next Steps

Once Agent Builder is working:
1. Run our setup script to load sample data
2. Create the LogSleuth tools (Phase 2)
3. Build the full investigation agent

---

## Resources

- [Official Docs: Get Started](https://www.elastic.co/docs/solutions/search/agent-builder/get-started)
- [Agent Builder Product Page](https://www.elastic.co/elasticsearch/agent-builder)
- [API Documentation](https://www.elastic.co/docs/api/doc/kibana/operation/operation-post-agent-builder-agents)
- [Free Training Course](https://www.elastic.co/training/elastic-ai-agents-mcp)
- [Tutorial: Your First Agent](https://www.elastic.co/search-labs/blog/ai-agent-builder-elasticsearch)
