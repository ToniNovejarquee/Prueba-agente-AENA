# POC integración agéntica Aerolínea ↔ AENA (MuleSoft MCP + A2A + LLM)

Un usuario escribe en el **chat de GitHub Copilot**: *"Hola, quiero un vuelo de Madrid a Londres el 20 de noviembre"*.

1. Copilot llama por **MCP** al **adaptador MCP de la aerolínea**, que reenvía la petición por **A2A** al **agente de la aerolínea**.
2. El agente de la aerolínea delega por **A2A** en el **agente de AENA** todo lo aeroportuario: vuelos, parking y pagos.
3. El agente de AENA razona con un **LLM (Ollama Cloud, `gpt-oss:120b`)**, que elige la tool de sus **MCP bridges**. Cada bridge recubre una API.
4. Las reservas las gestiona el agente de la aerolínea con **su propio LLM** y su **MCP de reservas**, que recubre la API de reservas.
5. Copilot recibe un resumen legible y el detalle JSON, y sigue la conversación: elegir vuelo, reservar, añadir parking, pagar y confirmar.

Todo vive en **una única Mule App** (`poc-aena-vuelos`), dividida en **segmentos**: un XML por pieza en `src/main/mule`. Los segmentos **solo se comunican por protocolo** (A2A, MCP o HTTP), nunca con `flow-ref` entre ellos. Así cualquier segmento se puede sacar a otra app sin tocar su lógica. Es el mismo enfoque que la POC banca-seguros.

```
 GitHub Copilot ──MCP──▶ aerolinea-adaptador-mcp ──A2A──▶ aerolinea-agente ──────────A2A (Client ID)──────────▶ aena-agente ──▶ LLM (ollama.com)
 (chat VS Code o app)    6 tools para Copilot              │  LLM decide la tool de reservas                         │  el LLM decide la tool
                                                           ▼                                                         ▼
                                              aerolinea-mcp-reservas                         aena-mcp-vuelos   aena-mcp-parking   aena-mcp-pagos
                                                           │ HTTP                                 │ HTTP            │ HTTP              │ HTTP
                                                           ▼                                      ▼                 ▼                   ▼
                                              aerolinea-reservas-api                         aena-vuelos-api   aena-parking-api   aena-pagos-api + página de pago
                                              (mock + Object Store)                          (mock)            (mock + OS)        (mock Sipay + OS)
```

## Estructura

```
poc-aena-vuelos/
├── pom.xml                                 runtime 4.11.5; conectores HTTP, A2A, MCP, Inference y Object Store
├── src/main/mule/
│   ├── global.xml                          configuración (YAML) + único HTTP listener (puerto 8081)
│   ├── comun.xml                           trazabilidad, logging JSON, API key y gestión de errores
│   ├── aerolinea-adaptador-mcp.xml         AEROLÍNEA  servidor MCP para GitHub Copilot -> A2A al agente de la aerolínea
│   ├── aerolinea-agente.xml                AEROLÍNEA  agente A2A: orquesta, LLM + MCP reservas, A2A a AENA
│   ├── aerolinea-mcp-reservas.xml          AEROLÍNEA  servidor MCP: crear_reserva, consultar_reserva, actualizar_reserva
│   ├── aerolinea-reservas-api.xml          AEROLÍNEA  API REST de reservas (mock, Object Store)
│   ├── aena-agente.xml                     AENA       agente A2A con LLM y las tools de los 3 MCP bridges
│   ├── aena-mcp-vuelos.xml                 AENA       MCP bridge: buscar_vuelos, consultar_vuelo
│   ├── aena-mcp-parking.xml                AENA       MCP bridge: buscar_parking, reservar_parking
│   ├── aena-mcp-pagos.xml                  AENA       MCP bridge: crear_pago, estado_pago
│   ├── aena-vuelos-api.xml                 AENA       API de vuelos (mock determinista)
│   ├── aena-parking-api.xml                AENA       API de parking (mock, Object Store)
│   └── aena-pagos-api.xml                  AENA       API de pagos (mock Sipay, Object Store) + página de pago HTML
├── src/main/resources/
│   ├── config/poc-global.yaml              configuración GLOBAL: rutas, timeouts, logging, LLM
│   ├── config/aerolinea.yaml               configuración de la aerolínea (LLM sí/no, reintentos...)
│   ├── config/aena.yaml                    configuración de AENA y tarifas de los mocks
│   ├── dwl/comun/utilidades.dwl            búsqueda tolerante de resultados (MCP, A2A, LLM) y formato de euros
│   ├── dwl/aena/                           aeropuertos, generador de vuelos, tarifas de parking y página de pago
│   ├── dwl/aerolinea/resumen.dwl           texto que recibe Copilot (con el "siguiente paso")
│   └── log4j2.xml
├── pruebas/                                pruebas.http (REST Client), mcp_client.py y .env.example
└── .vscode/mcp.json                        registro del servidor MCP para el chat de GitHub Copilot en VS Code
```

## Rutas (todas en `http://localhost:8081`)

| Segmento | Ruta | Qué es |
|---|---|---|
| aerolinea-adaptador-mcp | `/aerolinea/mcp` | **Servidor MCP para Copilot** (6 tools) |
| aerolinea-agente | `/aerolinea/agente` | Agente A2A: Agent Card en `/.well-known/agent-card.json`, JSON-RPC en `/rpc` |
| aerolinea-mcp-reservas | `/aerolinea/mcp-reservas` | Servidor MCP de reservas |
| aerolinea-reservas-api | `/aerolinea/api/v1/reservas` | API de reservas (POST, GET y PATCH `/{localizador}`) |
| aena-agente | `/aena/agente` | Agente A2A de AENA |
| aena-mcp-vuelos / parking / pagos | `/aena/mcp-vuelos`, `/aena/mcp-parking`, `/aena/mcp-pagos` | MCP bridges |
| aena-vuelos-api | `/aena/api/b2b-flights/v1/vuelos/...` | `POST /busqueda`, `GET /{vueloId}` |
| aena-parking-api | `/aena/api/b2b-parking/v1/...` | `POST /disponibilidad`, `POST /reservas`, `GET /reservas/{codigo}` |
| aena-pagos-api | `/aena/api/b2b-payments/v1/pagos` | `POST /pagos`, `GET /pagos/{idPago}` |
| página de pago | `/aena/sipay/pago/{idPago}` | HTML que abre el usuario (sin API key) |

Todas exigen la API key de la POC en la cabecera `X-API-Key`. Las excepciones son las Agent Cards (públicas, como define A2A) y la página de pago, que abre el navegador del usuario.

## Tools que ve Copilot

| Tool | Qué hace | Pasa por |
|---|---|---|
| `buscar_vuelos` | Vuelos de origen a destino en una fecha. Acepta ciudad o código IATA | aerolínea → A2A → AENA (LLM) → MCP vuelos |
| `reservar_vuelo` | Reserva el vuelo elegido y devuelve el localizador | AENA `consultar_vuelo` (precio y plazas) → LLM aerolínea → `crear_reserva` |
| `buscar_parking` | Opciones y precios del parking AENA. Con el localizador, el aeropuerto y la entrada salen del vuelo | AENA (LLM) → MCP parking |
| `reservar_parking` | Añade el parking a la reserva y recalcula el total | AENA `reservar_parking` → LLM aerolínea → `actualizar_reserva` |
| `pagar_reserva` | Crea el pago por el total y devuelve el **enlace de pago** | AENA `crear_pago` → LLM aerolínea → `actualizar_reserva` |
| `consultar_reserva` | Estado de la reserva. Si el pago estaba pendiente, lo comprueba y confirma la reserva | MCP reservas → AENA `estado_pago` → `actualizar_reserva` |

Las descripciones de las tools le dicen a Copilot qué preguntar al usuario (titular, fecha de recogida del coche…), y cada respuesta incluye el **siguiente paso**. Así Copilot guía la conversación solo.

## Requisitos

- Anypoint Studio 7.x con runtime Mule **4.11.x EE** (o Anypoint Code Builder). JDK 17.
- Una **API key de ollama.com**. No hace falta tener Ollama instalado.
- VS Code con **GitHub Copilot Chat** (modo *Agent*), o la app de escritorio de GitHub Copilot.
- Python 3 (opcional, para `pruebas/mcp_client.py`).

## Ejecutar

1. **Importar en Studio**: *File → Import → Anypoint Studio → Anypoint Studio project from File System* y elige esta carpeta. Studio descargará los conectores del `pom.xml`: Inference y Object Store son nuevos respecto a la versión anterior.
2. **Generar una API key para la POC** (PowerShell):
   ```powershell
   ((New-Guid).Guid + (New-Guid).Guid).Replace('-', '')
   ```
3. *Run Configurations → poc-aena-vuelos → Arguments → VM arguments*:
   ```text
   -Dpoc.seguridad.apiKey=<API key de la POC> -Dpoc.llm.apiKey=<API key de ollama.com> -Djavax.net.ssl.trustStoreType=Windows-ROOT
   ```
   El último argumento solo hace falta en redes con inspección TLS (proxy corporativo tipo Netskope). Sin él, la llamada al LLM falla con `PKIX path building failed`.
   Las dos claves son obligatorias: sin ellas la app no arranca. **Ya no están en el YAML.**
4. *Run As → Mule Application*. Comprueba que arranca: abre `http://localhost:8081/aena/agente/.well-known/agent-card.json`.

> **Demo sin LLM** (más rápida, o si ollama.com no responde): añade `-Daerolinea.agente.usarLlm=false -Daena.agente.usarLlm=false`. Las tools se llaman directamente y el resto funciona igual. Sigue haciendo falta `-Dpoc.llm.apiKey` (cualquier valor), porque el conector Inference se configura al arrancar.

## Conectar el chat de GitHub Copilot

**VS Code (Copilot Chat)**
1. Abre esta carpeta en VS Code. `.vscode/mcp.json` ya registra el servidor `aerolinea-demo-viajes` → `http://localhost:8081/aerolinea/mcp`.
2. Abre `.vscode/mcp.json` y pulsa **Start** encima del servidor. VS Code **pide la API key** (la misma de `-Dpoc.seguridad.apiKey`) y la guarda cifrada.
3. En Copilot Chat elige el modo **Agent**. En el icono de herramientas deben aparecer las 6 tools de `aerolinea-demo-viajes`.

**App de escritorio GitHub Copilot**
- Los servidores MCP se gestionan en *Customize → MCP* y se guardan en `%USERPROFILE%\.copilot\mcp-config.json`. Si el formulario no permite cabeceras, cierra la app, edita el fichero y vuelve a abrirla:
  ```json
  "aerolinea-demo-viajes": {
    "tools": ["*"],
    "type": "http",
    "url": "http://localhost:8081/aerolinea/mcp",
    "headers": { "X-API-Key": "<tu API key>" }
  }
  ```

### Guion de la demo (en un chat nuevo)

1. *"Hola, quiero un vuelo de Madrid a Londres el 20 de noviembre"* → Copilot muestra 4 vuelos con horarios y precios.
2. *"El segundo. Soy Ana López, ana.lopez@example.com"* → reserva con localizador, pendiente de pago.
3. *"Quiero dejar el coche en Barajas, vuelvo el 27"* → opciones de parking AENA con precio.
4. *"El general"* → parking añadido y total recalculado.
5. *"Vale, quiero pagar"* → enlace a la página de pago. Ábrelo, pulsa **Pagar**.
6. *"Ya he pagado"* → Copilot consulta la reserva: **CONFIRMADA**.

Para seguir una petición de punta a punta, filtra `poc-aena-vuelos.log` por su `correlationId`.

**Sin Copilot**: `pruebas/pruebas.http` (extensión REST Client; copia `pruebas/.env.example` a `pruebas/.env` y pon la API key) o:
```bash
python pruebas/mcp_client.py http://localhost:8081/aerolinea/mcp buscar_vuelos '{"origen":"Madrid","destino":"Londres","fecha":"2026-11-20"}' "--header=X-API-Key=<tu API key>"
```

## Configuración

- **`config/poc-global.yaml`**: rutas, timeouts, logging y LLM. **`config/aerolinea.yaml`** y **`config/aena.yaml`**: lo de cada dominio.
- Cualquier valor se sobrescribe sin recompilar con `-D<propiedad>=<valor>`, por ejemplo `-Dpoc.logging.nivel=INFO`.
- `*.agente.usarLlm`: `true` hace que el LLM decida la tool. `false` llama a la tool directamente.
- `*.agente.fallbackDeterminista`: si el LLM falla o no ejecuta la tool, se llama directamente y se registra como `WARN`, con `origenCalculo`/`origenReservas = FALLBACK_TOOL_DIRECTA`.
- **Timeouts**: cada salto exterior espera más que la suma de los interiores. La regla está comentada en `poc-global.yaml`.

## Mocks

- **Vuelos**: no hay base de datos. Para una ruta y una fecha siempre salen los mismos vuelos: 4 al día en corto y medio radio, 2 en largo radio. La duración sale de la distancia real entre aeropuertos y el precio de las tarifas en `aena.yaml`. El `vueloId` (`DA1234_MADLHR_20261120`) codifica la ruta y la fecha.
- **Aeropuertos**: MAD, BCN, AGP, PMI, SVQ, VLC, ALC, BIO, LPA, TFN (red AENA, con parking) y LHR, CDG, FCO, AMS, LIS, FRA, JFK. Acepta nombres de ciudad ("Londres", "Barcelona"…).
- **Parking, pagos y reservas**: Object Store en memoria. **Se pierden al reiniciar la app.**
- **Página de pago**: simula la pasarela tipo Sipay. No pide ni guarda datos de tarjeta.

## Cambios respecto a la versión anterior

- **Entrada para Copilot**: nuevo servidor MCP `/aerolinea/mcp`. Antes Copilot no tenía por dónde entrar, porque la aerolínea solo era servidor A2A.
- **Cadena completa**: la aerolínea ahora llama a AENA por A2A (cliente A2A + `send-message`). Antes respondía "Solicitud recibida" y terminaba.
- **Argumentos MCP**: se evaluaban como texto literal (`#[payload]` entre saltos de línea) y pasaban el mensaje A2A entero. Ahora se extrae el DataPart.
- **Body de las tools**: las tools enviaban a la API el payload Java sin convertir. Ahora mandan JSON y propagan `x-correlation-id`.
- **Búsqueda real**: se busca por origen, destino y fecha. Antes solo por `flightNumber`, y el mock devolvía siempre IB1234.
- **Pagos**: los IDs ya no están hardcodeados (antes `REQ-001` frente a `PAY-001`). Hay estado real del pago y página de pago.
- **Versiones**: runtime 4.11.5, coherente con `mule-artifact.json` y con A2A 2.0. Se añaden Inference y Object Store y se quita `sockets`.
- **Flujo por pasos**: AENA ya no hace vuelo + parking + pago de golpe. Cada paso lo decide el usuario en la conversación.
- **Seguridad**: la API key se valida en todos los componentes y ya no está en el YAML.
- **LLM en los dos agentes**, con salvaguarda determinista.
- **MCP y API de reservas de la aerolínea**, como en el diagrama.
- **Trazas, errores y documentación**: logging JSON con `correlationId`, errores de negocio como datos (`{tipo: "error"}`), rutas con prefijo, README, pruebas y `.vscode/mcp.json`.

## Siguientes pasos

- **Omni Gateway de AENA**: poner Flex Gateway delante de los MCP y las APIs de AENA y sustituir la API key por el **Client ID de la aerolínea** (Client ID Enforcement, rate limiting) con API Autodiscovery.
- Mocks reales del diagrama (FastAPI y PostgreSQL): basta con apuntar los `http:request-config` de los MCP bridges a esos servicios.
- Canal "chat en la app" de la aerolínea: ya puede hablar A2A con `/aerolinea/agente` enviando `{accion, datos}`.
- CloudHub 2.0: igual que banca-seguros (propiedades protegidas, una réplica; `poc.urlPublica` sí hace falta, para que el enlace de pago apunte a la URL pública).
