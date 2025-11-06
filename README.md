# 🤖 Banking Agent Framework

Sistema multi-agente inteligente para asesoramiento bancario con control de cumplimiento normativo integrado. Construido sobre **Microsoft Agent Framework** con integración de **Azure AI** y **Copilot Studio**.

## 📋 Descripción

Este framework implementa un flujo conversacional avanzado para asesoramiento de productos bancarios que combina:

- **Análisis inteligente de necesidades** del cliente
- **Consulta de expertos** mediante agentes especializados
- **Comunicación en lenguaje claro** adaptado al usuario final
- **Validación de cumplimiento normativo** automática
- **Revisión iterativa** con bucle de retroalimentación

### 🔄 Flujo del Workflow

```
Cliente → Need Profiler → Product Expert → Clarity Writer → Compliance Checker
                                                                      ↓
                                                            [Aprobado / Rechazado]
                                                                      ↓
                                                            Publisher ← Loop Revision
```

## 🏗️ Arquitectura

El sistema se compone de **5 agentes especializados**:

1. **Need Profiler** (Azure AI Agent)
   - Analiza la consulta del cliente
   - Identifica tipo de producto, perfil y restricciones
   - Detecta información faltante
   - Genera query estructurado

2. **Product Expert** (Copilot Studio Agent)
   - Especialista en productos bancarios
   - Acceso a conocimiento específico del dominio
   - Responde consultas técnicas de productos

3. **Clarity Writer** (Azure AI Agent)
   - Traduce jerga técnica a lenguaje claro
   - Estructura información de forma comprensible
   - Genera resumen, pros/cons y llamada a la acción

4. **Compliance Checker** (Azure AI Agent)
   - Valida cumplimiento normativo financiero
   - Verifica disclaimers obligatorios
   - Detecta recomendaciones no permitidas
   - Genera feedback para correcciones

5. **Publisher** (Azure AI Agent)
   - Formatea respuesta final
   - Añade estructura markdown profesional
   - Incluye disclaimers estándar
   - Prepara contenido listo para publicación

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.10 o superior
- Cuenta de Azure con acceso a:
  - Azure AI Foundry / Azure AI Studio
  - Azure OpenAI Service
- Copilot Studio configurado (opcional, según implementación)
- Autenticación Azure configurada

### Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd sabadellAgentFramework
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate     # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales reales
   ```

5. **Autenticarse en Azure**
   ```bash
   az login
   ```

### Ejecución

#### Opción 1: Agente Básico (Demo)
```bash
python 1.SabadellBasicAgent.py
```

#### Opción 2: Copilot Studio Agent
```bash
python 2.CopilotAgent.py
```

#### Opción 3: Workflow Completo (Recomendado)
```bash
python 3.MAFAdvisorWorkflow.py
```

#### Opción 4: Workflow con Email Agent
```bash
python 4.SabadellAdvisorWorkflowEmail.py
```

La interfaz DevUI se abrirá automáticamente en tu navegador por defecto en `http://localhost:8091`.

## 📁 Estructura del Proyecto

```
sabadellAgentFramework/
│
├── 1.SabadellBasicAgent.py           # Agente básico de demostración
├── 2.CopilotAgent.py                 # Agente standalone de Copilot Studio
├── 3.MAFAdvisorWorkflow.py           # Workflow completo principal
├── 4.SabadellAdvisorWorkflowEmail.py # Workflow con agente de email
│
├── requirements.txt                   # Dependencias Python
├── .env.example                      # Template de configuración
├── .env                              # Configuración local (no incluir en Git)
│
└── README.md                         # Este archivo
```

## ⚙️ Configuración

### Variables de Entorno Requeridas

Consulta el archivo `.env.example` para ver todas las variables necesarias:

- **Copilot Studio**: Environment ID, Tenant ID, Agent App ID, Schema Name
- **Azure OpenAI**: Deployment Name, API Key, Endpoint
- **Azure AI Foundry**: Project Endpoint, Model Deployment Name
- **Telemetry**: ENABLE_OTEL para observabilidad

### Autenticación Azure

El proyecto usa `DefaultAzureCredential` que soporta múltiples métodos:

1. **Azure CLI** (recomendado para desarrollo)
   ```bash
   az login
   ```

2. **Variables de entorno**
   ```bash
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_TENANT_ID="your-tenant-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   ```

3. **Managed Identity** (para producción en Azure)

## 🔧 Características Avanzadas

### Routing Condicional

El workflow implementa enrutamiento dinámico basado en condiciones:

- **Información incompleta** → Solicita datos adicionales al usuario
- **Información completa** → Procede al flujo principal
- **Compliance aprobado** → Publica respuesta final
- **Compliance rechazado** → Loop de revisión con el Clarity Writer

### Structured Outputs

Todos los agentes usan **Pydantic models** para respuestas estructuradas:

```python
class NeedProfile(BaseModel):
    product_type: str
    customer_type: str
    key_constraints: list[str]
    missing_info: list[str]
    structured_query: str
```

### Persistent Token Cache

Autenticación persistente para Copilot Studio:

```python
cache_location = os.path.join(os.path.expanduser("~"), ".copilot_token_cache.bin")
token_cache = PersistedTokenCache(FilePersistence(cache_location))
```

### Telemetría y Observabilidad

Habilitada mediante OpenTelemetry (`ENABLE_OTEL=true`) para:
- Trazabilidad end-to-end
- Debugging de workflows
- Análisis de rendimiento

## 📊 Casos de Uso

### Ejemplo 1: Consulta de Hipoteca
```
Usuario: "Quiero una hipoteca a tipo fijo, gano 3000€/mes"
↓
Need Profiler: Identifica producto, perfil, constraints
↓
Product Expert: Consulta opciones de hipotecas fijas
↓
Clarity Writer: Explica en lenguaje claro
↓
Compliance: Valida disclaimers y regulación
↓
Publisher: Formatea respuesta profesional
```

### Ejemplo 2: Información Incompleta
```
Usuario: "Necesito información del banco"
↓
Need Profiler: Detecta missing_info
↓
Sistema: "📋 Necesitamos más información: ¿Qué tipo de producto te interesa?"
[Workflow termina, espera respuesta del usuario]
```

## 🛠️ Desarrollo

### Añadir Nuevos Agentes

```python
new_agent = AgentExecutor(
    agent_client.create_agent(
        name="My Custom Agent",
        instructions="...",
        response_format=MyModel,
    ),
    id="my_agent",
)
```

### Crear Bridge Executors

```python
@executor(id="my_bridge")
async def my_bridge(
    response: AgentExecutorResponse,
    ctx: WorkflowContext[AgentExecutorRequest]
) -> None:
    # Transform and forward
    message = transform(response)
    await ctx.send_message(message)
```

### Definir Condiciones de Routing

```python
def my_condition(message: Any) -> bool:
    if not isinstance(message, AgentExecutorResponse):
        return False
    # Your logic here
    return True
```

## 📝 Buenas Prácticas

### Seguridad
- ✅ Nunca subir `.env` a control de versiones
- ✅ Usar Azure Key Vault en producción
- ✅ Rotar claves regularmente
- ✅ Aplicar principio de mínimo privilegio

### Compliance
- ✅ Siempre incluir disclaimers obligatorios
- ✅ No dar recomendaciones personalizadas sin perfil completo
- ✅ Validar contenido antes de publicar
- ✅ Mantener logs de auditoría

### Rendimiento
- ✅ Usar token cache persistente
- ✅ Implementar timeouts apropiados
- ✅ Monitorizar con OpenTelemetry
- ✅ Optimizar prompts de agentes

## 🧪 Testing

```bash
# Ejecutar tests (cuando estén disponibles)
pytest tests/

# Limpiar cache
python cleaner.py
```

## 📚 Recursos Adicionales

- [Microsoft Agent Framework Documentation](https://github.com/microsoft/agent-framework)
- [Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-studio/)
- [Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)

## 🤝 Contribución

Este es un proyecto interno. Para contribuir:

1. Crear una rama feature
2. Implementar cambios con tests
3. Asegurar que pasa compliance checks
4. Crear Pull Request con descripción detallada

## 📄 Licencia

Proyecto interno - Todos los derechos reservados.

## 🆘 Soporte

Para problemas o preguntas:
- Revisar logs de DevUI y terminal
- Verificar configuración en `.env`
- Comprobar autenticación Azure (`az account show`)
- Validar permisos en Azure AI y Copilot Studio

---

**⚠️ Nota**: Este sistema maneja información financiera sensible. Asegurar cumplimiento con regulaciones locales (GDPR, PSD2, etc.) antes de desplegar en producción.
