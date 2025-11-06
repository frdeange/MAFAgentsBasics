# ============================================================================
# SABADELL ADVISOR WORKFLOW: Product Advisory + Compliance Control
# ============================================================================
# Flujo: Cliente pregunta → Need Profiler → Sabadell Copilot Expert →
#        Clarity Writer → Compliance Checker → [Approved → Publisher | Rejected → Loop]
# ============================================================================
import os
import asyncio
import logging
from typing import Any
from dotenv import load_dotenv
from agent_framework import (
    WorkflowBuilder,
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    ChatMessage,
    Role,
    WorkflowContext,
    executor,
)
from agent_framework.azure import AzureAIAgentClient
from agent_framework.microsoft import CopilotStudioAgent
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel

load_dotenv()


# ============================================================================
# STRUCTURED OUTPUT MODELS
# ============================================================================

class NeedProfile(BaseModel):
    """Cliente need analysis result."""
    product_type: str  # hipoteca, cuenta, tarjeta, préstamo
    customer_type: str  # nuevo, existente, autónomo, empresa
    key_constraints: list[str]  # tipo fijo, sin comisiones, online only, etc.
    missing_info: list[str]  # información que falta: ingresos, residencia, etc.
    structured_query: str  # Query estructurado para el Copilot Agent


class ClarityExplanation(BaseModel):
    """Clear explanation for end customer."""
    summary: str  # Explicación sencilla
    pros_cons: list[str]  # Lista corta de pros y contras
    cta: str  # Call to action: qué hacer a continuación
    full_content: str  # Contenido completo para review


class ComplianceReview(BaseModel):
    """Compliance checker decision."""
    approved: bool  # True = approved, False = needs revision
    issues: list[str]  # Problemas detectados
    feedback: str  # Cómo corregir
    content: str  # El contenido revisado


class FinalResponse(BaseModel):
    """Final published response."""
    content: str


# ============================================================================
# CONDITIONAL ROUTING FUNCTIONS
# ============================================================================

def approved_condition(message: Any) -> bool:
    """Route to publisher only if compliance approved."""
    if not isinstance(message, AgentExecutorResponse):
        return True
    
    try:
        review = ComplianceReview.model_validate_json(message.agent_run_response.text)
        return review.approved
    except Exception:
        return False


def rejected_condition(message: Any) -> bool:
    """Route to clarity writer only if compliance rejected."""
    if not isinstance(message, AgentExecutorResponse):
        return True
    
    try:
        review = ComplianceReview.model_validate_json(message.agent_run_response.text)
        return not review.approved
    except Exception:
        return False


def missing_info_condition(message: Any) -> bool:
    """Check if we need more info from user."""
    if not isinstance(message, AgentExecutorResponse):
        return False
    
    try:
        profile = NeedProfile.model_validate_json(message.agent_run_response.text)
        return len(profile.missing_info) > 0
    except Exception:
        return False


def has_complete_info_condition(message: Any) -> bool:
    """Check if we can proceed to Copilot Agent."""
    if not isinstance(message, AgentExecutorResponse):
        return False
    
    try:
        profile = NeedProfile.model_validate_json(message.agent_run_response.text)
        has_info = len(profile.missing_info) == 0
        return has_info
    except Exception as e:
        # Si hay error parseando, asumimos que NO podemos continuar
        print(f"Error parsing NeedProfile: {e}")
        return False


# ============================================================================
# BRIDGE EXECUTORS (Transformers between stages)
# ============================================================================

@executor(id="to_copilot_query")
async def to_copilot_query(
    response: AgentExecutorResponse, 
    ctx: WorkflowContext[AgentExecutorRequest]
) -> None:
    """Convert need profile into Copilot Studio query."""
    profile = NeedProfile.model_validate_json(response.agent_run_response.text)
    
    # Create structured query for Copilot Studio
    copilot_query = ChatMessage(
        Role.USER,
        text=profile.structured_query
    )
    await ctx.send_message(AgentExecutorRequest(messages=[copilot_query], should_respond=True))


@executor(id="to_clarity_request")
async def to_clarity_request(
    response: AgentExecutorResponse,
    ctx: WorkflowContext[AgentExecutorRequest]
) -> None:
    """Convert Copilot response into clarity writer request."""
    # El texto del Copilot Studio contiene la info de productos
    copilot_output = response.agent_run_response.text
    
    clarity_msg = ChatMessage(
        Role.USER,
        text=f"Reescribe esta información de productos bancarios en lenguaje claro para el cliente:\n\n{copilot_output}"
    )
    await ctx.send_message(AgentExecutorRequest(messages=[clarity_msg], should_respond=True))


@executor(id="to_clarity_revision")
async def to_clarity_revision(
    response: AgentExecutorResponse,
    ctx: WorkflowContext[AgentExecutorRequest]
) -> None:
    """Convert compliance feedback into revision request."""
    review = ComplianceReview.model_validate_json(response.agent_run_response.text)
    
    # Create revision request with compliance feedback
    revision_msg = ChatMessage(
        Role.USER,
        text=(
            f"Por favor, revisa el contenido según este feedback de cumplimiento normativo:\n\n"
            f"PROBLEMAS DETECTADOS:\n" + "\n".join(f"- {issue}" for issue in review.issues) + "\n\n"
            f"FEEDBACK:\n{review.feedback}\n\n"
            f"CONTENIDO ORIGINAL:\n{review.content}"
        )
    )
    await ctx.send_message(AgentExecutorRequest(messages=[revision_msg], should_respond=True))


@executor(id="request_more_info")
async def request_more_info(
    response: AgentExecutorResponse,
    ctx: WorkflowContext[None, str]
) -> None:
    """Request missing information from user."""
    profile = NeedProfile.model_validate_json(response.agent_run_response.text)
    
    missing_items = "\n".join(f"- {item}" for item in profile.missing_info)
    output = (
        f"📋 **Necesitamos más información para ayudarte mejor:**\n\n"
        f"{missing_items}\n\n"
        f"Por favor, proporciona estos datos para poder ofrecerte las mejores opciones del Banco Sabadell."
    )
    await ctx.yield_output(output)


@executor(id="publish_final_response")
async def publish_final_response(
    response: AgentExecutorResponse,
    ctx: WorkflowContext[None, str]
) -> None:
    """Publish the final approved response."""
    try:
        final = FinalResponse.model_validate_json(response.agent_run_response.text)
        await ctx.yield_output(f"✅ **RESPUESTA FINAL:**\n\n{final.content}")
    except Exception as e:
        # Si falla el parseo JSON, mostrar el texto tal cual
        print(f"⚠️  Warning: Could not parse Publisher output as JSON: {e}")
        print(f"Raw output: {response.agent_run_response.text[:500]}")
        await ctx.yield_output(f"✅ **RESPUESTA FINAL:**\n\n{response.agent_run_response.text}")


# ============================================================================
# WORKFLOW CREATION
# ============================================================================

def create_sabadell_advisor_workflow():
    """Create the complete Sabadell advisor workflow with all agents."""
    
    # Create Azure AI Agent client for Azure agents
    agent_client = AzureAIAgentClient(
        async_credential=DefaultAzureCredential()
    )
    
    # ========================================================================
    # AGENT 1: NEED PROFILER (Azure Agent)
    # ========================================================================
    need_profiler = AgentExecutor(
        agent_client.create_agent(
            instructions=(
                "Eres un analista de necesidades financieras. Tu trabajo es interpretar la pregunta del cliente "
                "y estructurarla para facilitar la búsqueda de productos.\n\n"
                "Debes identificar:\n"
                "- product_type: tipo de producto (hipoteca, cuenta, tarjeta, préstamo, ahorro, inversión)\n"
                "- customer_type: perfil del cliente (nuevo, existente, autónomo, empresa, joven, senior)\n"
                "- key_constraints: características específicas que busca (tipo fijo, sin comisiones, online, vinculación)\n"
                "- missing_info: SOLO información ABSOLUTAMENTE CRÍTICA sin la cual NO SE PUEDE dar NINGUNA respuesta útil\n"
                "- structured_query: una pregunta bien formulada para el experto de productos\n\n"
                "IMPORTANTE sobre missing_info:\n"
                "- Deja este campo VACÍO [] si hay suficiente información para dar una respuesta general sobre productos\n"
                "- Solo marca missing_info si el cliente no ha dicho QUÉ producto quiere (ej: solo dice 'ayúdame con finanzas')\n"
                "- Detalles como edad exacta, importe exacto, residencia NO son críticos - el experto puede dar info general\n\n"
                "EJEMPLO 1 (información SUFICIENTE):\n"
                "Input: 'Quiero hipoteca tipo fijo, gano 3000€, soy nuevo cliente'\n"
                "Output: {\n"
                "  'product_type': 'hipoteca',\n"
                "  'customer_type': 'nuevo',\n"
                "  'key_constraints': ['tipo fijo', 'ingresos 3000€'],\n"
                "  'missing_info': [],\n"
                "  'structured_query': 'Cliente nuevo con ingresos de 3.000€/mes busca hipoteca a tipo fijo. "
                "Explica las opciones de hipotecas fijas del Banco Sabadell y sus condiciones generales.'\n"
                "}\n\n"
                "EJEMPLO 2 (información INSUFICIENTE):\n"
                "Input: 'Quiero información del banco'\n"
                "Output: {\n"
                "  'product_type': 'sin especificar',\n"
                "  'customer_type': 'sin especificar',\n"
                "  'key_constraints': [],\n"
                "  'missing_info': ['qué tipo de producto o servicio necesitas'],\n"
                "  'structured_query': ''\n"
                "}\n\n"
                "Devuelve siempre JSON con estos campos."
            ),
            name="Sabadell Need Profiler",
            response_format=NeedProfile,
        ),
        id="need_profiler",
    )
    
    # ========================================================================
    # AGENT 2: SABADELL PRODUCT EXPERT (Copilot Studio Agent)
    # ========================================================================
    # Configure token cache for persistent authentication
    from msal_extensions import (
        FilePersistence,
        PersistedTokenCache,
    )
    
    # Create a persistent token cache in the workspace
    cache_location = os.path.join(os.path.expanduser("~"), ".copilot_token_cache.bin")
    persistence = FilePersistence(cache_location)
    token_cache = PersistedTokenCache(persistence)
    
    sabadell_expert = AgentExecutor(
        CopilotStudioAgent(
            token_cache=token_cache,  # Use persistent token cache
        ),
        id="sabadell_copilot_expert",
    )
    
    # ========================================================================
    # AGENT 3: CLARITY WRITER (Azure Agent)
    # ========================================================================
    clarity_writer = AgentExecutor(
        agent_client.create_agent(
            instructions=(
                "Eres un comunicador financiero experto en lenguaje claro. Tu trabajo es reescribir "
                "información de productos bancarios en un formato fácil de entender para clientes finales.\n\n"
                "REGLAS ESTRICTAS:\n"
                "1. NO des recomendaciones personalizadas ('deberías contratar...', 'te conviene...')\n"
                "2. Solo presenta información objetiva de productos\n"
                "3. Usa lenguaje sencillo, sin jerga técnica\n"
                "4. Explica términos complejos (TIN, TAE, vinculación, etc.)\n"
                "5. Estructura la información claramente\n\n"
                "Devuelve JSON con:\n"
                "- summary: explicación general clara (2-3 párrafos)\n"
                "- pros_cons: lista de 3-5 puntos clave (ventajas y consideraciones)\n"
                "- cta: llamada a la acción específica (enlace web, teléfono, oficina)\n"
                "- full_content: el contenido completo formateado y listo para mostrar\n\n"
                "EJEMPLO de full_content:\n"
                "**Hipotecas a Tipo Fijo del Banco Sabadell**\n\n"
                "[Explicación clara]\n\n"
                "**Puntos clave:**\n- [pros/cons]\n\n"
                "**Próximos pasos:**\n[CTA específico]"
            ),
            name="Clarity Writer",
            response_format=ClarityExplanation,
        ),
        id="clarity_writer",
    )
    
    # ========================================================================
    # AGENT 4: COMPLIANCE & RISK CHECKER (Azure Agent)
    # ========================================================================
    compliance_checker = AgentExecutor(
        agent_client.create_agent(
            instructions=(
                "Eres un auditor de cumplimiento normativo financiero. Tu trabajo es verificar que "
                "las comunicaciones al cliente cumplan con regulaciones y buenas prácticas.\n\n"
                "VERIFICACIONES OBLIGATORIAS:\n"
                "1. ✓ NO hay recomendaciones personalizadas sin perfil completo\n"
                "2. ✓ SÍ hay disclaimer: 'Esta información no constituye asesoramiento financiero personalizado'\n"
                "3. ✓ SÍ hay referencia a consultar web oficial para condiciones actualizadas\n"
                "4. ✓ NO se inventan condiciones no mencionadas en la información original\n"
                "5. ✓ El lenguaje es informativo, no prescriptivo\n"
                "6. ✓ Se mencionan requisitos y condiciones importantes\n\n"
                "Devuelve JSON con:\n"
                "- approved: true si cumple TODAS las verificaciones\n"
                "- issues: lista de problemas específicos detectados (vacía si approved=true)\n"
                "- feedback: instrucciones claras de cómo corregir cada issue\n"
                "- content: el contenido revisado (para referencia)\n\n"
                "Sé estricto pero constructivo. El objetivo es proteger al cliente y al banco."
            ),
            name="Compliance & Risk Checker",
            response_format=ComplianceReview,
        ),
        id="compliance_checker",
    )
    
    # ========================================================================
    # AGENT 5: PUBLISHER (Azure Agent)
    # ========================================================================
    publisher = AgentExecutor(
        agent_client.create_agent(
            instructions=(
                "Eres el publicador final. Tu trabajo es dar el toque profesional definitivo al contenido aprobado "
                "y presentarlo de forma clara y atractiva para el cliente.\n\n"
                "TAREAS:\n"
                "1. Estructurar en secciones claras con títulos markdown (##, ###)\n"
                "2. Añadir emojis apropiados para mejorar legibilidad (🏠 💰 📊 ✓ ⚠️ 📞 🌐)\n"
                "3. Asegurar formato markdown consistente y profesional\n"
                "4. Incluir una sección introductoria amigable\n"
                "5. Añadir al final el disclaimer estándar del banco:\n\n"
                "---\n\n"
                "**ℹ️ Información importante:**\n"
                "- Esta información no constituye asesoramiento financiero personalizado\n"
                "- Las condiciones pueden variar según el perfil del cliente\n"
                "- Para información actualizada, consulta siempre bancsabadell.com\n"
                "- Banco Sabadell, S.A. - Inscrito en el Registro Mercantil de Barcelona\n\n"
                "6. Verificar que el CTA (llamada a la acción) es claro y accionable\n\n"
                "IMPORTANTE: Devuelve el resultado en formato JSON con el campo 'content' "
                "que contenga el texto completo formateado en markdown."
            ),
            name="Final Publisher",
            response_format=FinalResponse,
        ),
        id="publisher",
    )
    
    # ========================================================================
    # BUILD WORKFLOW WITH CONDITIONAL ROUTING
    # ========================================================================
    workflow = (
        WorkflowBuilder(
            name="Sabadell Product Advisor",
            description="Asesor de productos bancarios con control de cumplimiento normativo",
        )
        # Start: Customer question → Need Profiler
        .set_start_executor(need_profiler)
        
        # Path 1: Missing info → Request more info (terminal)
        .add_edge(need_profiler, request_more_info, condition=missing_info_condition)
        
        # Path 2: Complete info → Continue workflow
        # Need Profiler → Bridge → Copilot Expert (solo si NO falta info)
        .add_edge(need_profiler, to_copilot_query, condition=has_complete_info_condition)
        .add_edge(to_copilot_query, sabadell_expert)
        
        # Copilot Expert → Bridge → Clarity Writer
        .add_edge(sabadell_expert, to_clarity_request)
        .add_edge(to_clarity_request, clarity_writer)
        
        # Clarity Writer → Compliance Checker
        .add_edge(clarity_writer, compliance_checker)
        
        # Compliance approved → Publisher → Output
        .add_edge(compliance_checker, publisher, condition=approved_condition)
        .add_edge(publisher, publish_final_response)
        
        # Compliance rejected → Bridge → Clarity Writer (LOOP)
        .add_edge(compliance_checker, to_clarity_revision, condition=rejected_condition)
        .add_edge(to_clarity_revision, clarity_writer)
        
        .build()
    )
    
    return workflow


# ============================================================================
# MAIN: LAUNCH DEVUI
# ============================================================================

def main():
    """Launch the Sabadell advisor workflow in DevUI."""
    from agent_framework.devui import serve
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)
    
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 18 + "BANCO SABADELL - ADVISOR WORKFLOW" + " " * 27 + "║")
    print("║" + " " * 15 + "Asesor de Productos + Control de Cumplimiento" + " " * 18 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")
    
    logger.info("🚀 Creando Sabadell Product Advisor Workflow...")
    workflow = create_sabadell_advisor_workflow()
    
    logger.info("✅ Workflow creado exitosamente!")
    logger.info("🎯 Iniciando DevUI server...")
    logger.info("")
    
    # Launch server with the workflow and tracing enabled
    serve(
        entities=[workflow],
        port=8091,
        auto_open=True,
        tracing_enabled=True
    )

if __name__ == "__main__":
    main()
