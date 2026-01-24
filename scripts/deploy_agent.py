#!/usr/bin/env python3
"""
Deploy LogSleuth to Elastic Agent Builder.

This script deploys all tools and the agent configuration to
Elastic Agent Builder via the Kibana API.

Usage:
    python scripts/deploy_agent.py [--dry-run] [--tools-only] [--agent-only]

Options:
    --dry-run      Show what would be deployed without making changes
    --tools-only   Only deploy tools (skip agent creation)
    --agent-only   Only deploy agent (skip tools)
    --force        Overwrite existing tools and agent
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from dotenv import load_dotenv

load_dotenv()

# Get Kibana configuration
KIBANA_URL = os.getenv("KIBANA_URL", "").rstrip("/")
KIBANA_API_KEY = os.getenv("KIBANA_API_KEY", "")


def get_headers() -> dict:
    """Get headers for Kibana API requests."""
    return {
        "Authorization": f"ApiKey {KIBANA_API_KEY}",
        "Content-Type": "application/json",
        "kbn-xsrf": "true",
    }


def check_connection() -> bool:
    """Check connection to Kibana."""
    if not KIBANA_URL or not KIBANA_API_KEY:
        print("Error: KIBANA_URL and KIBANA_API_KEY must be set in .env")
        return False

    try:
        response = httpx.get(
            f"{KIBANA_URL}/api/status",
            headers=get_headers(),
            timeout=10.0,
        )
        if response.status_code == 200:
            status = response.json()
            print(f"Connected to Kibana: {status.get('name', 'Unknown')}")
            return True
        else:
            print(f"Error: Kibana returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"Error connecting to Kibana: {e}")
        return False


def list_existing_tools() -> list:
    """List existing tools in Agent Builder."""
    try:
        response = httpx.get(
            f"{KIBANA_URL}/api/agent_builder/tools",
            headers=get_headers(),
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json().get("tools", [])
        return []
    except Exception:
        return []


def list_existing_agents() -> list:
    """List existing agents in Agent Builder."""
    try:
        response = httpx.get(
            f"{KIBANA_URL}/api/agent_builder/agents",
            headers=get_headers(),
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json().get("agents", [])
        return []
    except Exception:
        return []


def deploy_tool(tool_definition: dict, force: bool = False, dry_run: bool = False) -> bool:
    """Deploy a single tool to Agent Builder."""
    tool_id = tool_definition["toolId"]
    print(f"\n  Deploying tool: {tool_id}")

    if dry_run:
        print(f"    [DRY RUN] Would create tool: {tool_id}")
        print(f"    Description: {tool_definition['description'][:60]}...")
        return True

    # Check if tool exists
    existing_tools = list_existing_tools()
    existing_ids = [t.get("toolId") or t.get("id") for t in existing_tools]

    if tool_id in existing_ids:
        if force:
            print(f"    Tool exists, updating...")
            # Delete first, then recreate (some APIs don't support PUT)
            try:
                httpx.delete(
                    f"{KIBANA_URL}/api/agent_builder/tools/{tool_id}",
                    headers=get_headers(),
                    timeout=10.0,
                )
            except Exception:
                pass
        else:
            print(f"    Tool already exists (use --force to overwrite)")
            return True

    # Create the tool
    try:
        response = httpx.post(
            f"{KIBANA_URL}/api/agent_builder/tools",
            headers=get_headers(),
            json=tool_definition,
            timeout=30.0,
        )

        if response.status_code in [200, 201]:
            print(f"    [OK] Tool created successfully")
            return True
        else:
            print(f"    [ERROR] Status {response.status_code}: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"    [ERROR] {e}")
        return False


def deploy_agent(agent_definition: dict, force: bool = False, dry_run: bool = False) -> bool:
    """Deploy the agent to Agent Builder."""
    agent_id = agent_definition["agentId"]
    print(f"\n  Deploying agent: {agent_id}")

    if dry_run:
        print(f"    [DRY RUN] Would create agent: {agent_id}")
        print(f"    Name: {agent_definition['name']}")
        print(f"    Tools: {', '.join(agent_definition['tools'])}")
        return True

    # Check if agent exists
    existing_agents = list_existing_agents()
    existing_ids = [a.get("agentId") or a.get("id") for a in existing_agents]

    if agent_id in existing_ids:
        if force:
            print(f"    Agent exists, updating...")
            try:
                httpx.delete(
                    f"{KIBANA_URL}/api/agent_builder/agents/{agent_id}",
                    headers=get_headers(),
                    timeout=10.0,
                )
            except Exception:
                pass
        else:
            print(f"    Agent already exists (use --force to overwrite)")
            return True

    # Create the agent
    try:
        response = httpx.post(
            f"{KIBANA_URL}/api/agent_builder/agents",
            headers=get_headers(),
            json=agent_definition,
            timeout=30.0,
        )

        if response.status_code in [200, 201]:
            print(f"    [OK] Agent created successfully")
            return True
        else:
            print(f"    [ERROR] Status {response.status_code}: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"    [ERROR] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Deploy LogSleuth to Agent Builder")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deployed")
    parser.add_argument("--tools-only", action="store_true", help="Only deploy tools")
    parser.add_argument("--agent-only", action="store_true", help="Only deploy agent")
    parser.add_argument("--force", action="store_true", help="Overwrite existing resources")
    args = parser.parse_args()

    print("=" * 60)
    print("LogSleuth Agent Builder Deployment")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    # Check connection
    print("\n[1] Checking Kibana connection...")
    if not args.dry_run and not check_connection():
        print("\nFailed to connect to Kibana. Please check:")
        print("  1. KIBANA_URL is set correctly in .env")
        print("  2. KIBANA_API_KEY is valid")
        print("  3. Agent Builder is enabled in your deployment")
        sys.exit(1)
    elif args.dry_run:
        print(f"  KIBANA_URL: {KIBANA_URL or '[NOT SET]'}")
        print(f"  KIBANA_API_KEY: {'[SET]' if KIBANA_API_KEY else '[NOT SET]'}")

    # Import tool and agent definitions
    from src.tools import ALL_TOOL_DEFINITIONS
    from src.agent.logsleuth_agent import AGENT_DEFINITION

    # Deploy tools
    if not args.agent_only:
        print(f"\n[2] Deploying {len(ALL_TOOL_DEFINITIONS)} tools...")
        tools_success = 0
        for tool in ALL_TOOL_DEFINITIONS:
            # Skip non-ES|QL tools for now (save_investigation is custom)
            if tool.get("type") == "custom":
                print(f"\n  Skipping {tool['toolId']} (custom tool - manual setup required)")
                continue

            if deploy_tool(tool, force=args.force, dry_run=args.dry_run):
                tools_success += 1

        print(f"\n  Tools deployed: {tools_success}/{len(ALL_TOOL_DEFINITIONS)}")

    # Deploy agent
    if not args.tools_only:
        print("\n[3] Deploying agent...")

        # Filter out custom tools from agent's tool list
        esql_tool_ids = [
            t["toolId"] for t in ALL_TOOL_DEFINITIONS
            if t.get("type") != "custom"
        ]

        agent_config = AGENT_DEFINITION.copy()
        agent_config["tools"] = [t for t in agent_config["tools"] if t in esql_tool_ids]

        deploy_agent(agent_config, force=args.force, dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes were made")
        print("\nTo deploy for real, run:")
        print("  python scripts/deploy_agent.py")
    else:
        print("DEPLOYMENT COMPLETE")
        print("\nNext steps:")
        print("  1. Open Kibana and go to Agents")
        print("  2. Select 'LogSleuth - Incident Investigator' from the agent dropdown")
        print("  3. Try asking: 'What errors occurred in the last hour?'")
    print("=" * 60)


def export_definitions():
    """Export tool and agent definitions as JSON files."""
    from src.tools import ALL_TOOL_DEFINITIONS
    from src.agent.logsleuth_agent import AGENT_DEFINITION

    output_dir = project_root / "config"
    output_dir.mkdir(exist_ok=True)

    # Export tools
    tools_file = output_dir / "tools.json"
    with open(tools_file, "w") as f:
        json.dump(ALL_TOOL_DEFINITIONS, f, indent=2)
    print(f"Exported tools to: {tools_file}")

    # Export agent
    agent_file = output_dir / "agent.json"
    with open(agent_file, "w") as f:
        json.dump(AGENT_DEFINITION, f, indent=2)
    print(f"Exported agent to: {agent_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        export_definitions()
    else:
        main()
