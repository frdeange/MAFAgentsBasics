from agent_framework import HostedMCPTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity import DefaultAzureCredential
from agent_framework.devui import serve

# Creamos el cliente de Azure AI con las credenciales predeterminadas
azure_client = AzureAIAgentClient(async_credential=DefaultAzureCredential())

# Ahora creamos el Agente Usando el Cliente de Azure AI
sabadell_agent = azure_client.create_agent(
    name="Agente Bancario Sabadell",
    description="Asesor bancario virtual especializado en productos y servicios del Banco Sabadell.",
    instructions="Proporciona asesoramiento financiero personalizado a los clientes del Banco Sabadell, incluyendo información sobre hipotecas, préstamos, cuentas de ahorro e inversiones.",
    tools=[]
)

# Arrancamos el agente con la interfaz de usuario de desarrollo
serve(
    entities=[sabadell_agent],
    auto_open=True
)

