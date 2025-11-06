import asyncio
from agent_framework.microsoft import CopilotStudioAgent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.devui import serve
from azure.identity import DefaultAzureCredential

# Create agent using environment variables
Sabadell_Copilot_Agent = CopilotStudioAgent()

# Launch DevUI web server
serve(
    entities=[Sabadell_Copilot_Agent],
    auto_open=True,
    port=7860,
)