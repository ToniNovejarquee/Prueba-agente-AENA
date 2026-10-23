%dw 2.0
/*
 * Utilidades comunes (módulo DataWeave): import * from dwl::comun::utilidades
 *
 * Las respuestas de los conectores llegan con formas distintas según el camino:
 *   - MCP call-tool: objeto, CallToolResponse o texto JSON.
 *   - Inference [MCP] Tooling: {response, tools[], toolsExecutionReport[{tool, result}]}.
 *   - A2A send-message: la Task directa o envuelta ({task: ...}), con DataParts o texto JSON.
 * Por eso se busca de forma tolerante y recursiva.
 *
 * Contrato de la POC: todo resultado de negocio (de las APIs, las tools y los agentes) es un objeto
 * JSON con la clave "tipo" (p. ej. "vuelos", "reserva", "pago" o "error").
 */
import try from dw::Runtime

fun primero(xs) = (xs filter ($ != null))[0]

// Primer objeto (en profundidad) que cumple el predicado. Recorre objetos, arrays y textos JSON.
fun buscar(v, cumple) = v match {
    case o is Object -> if (cumple(o)) o else primero(valuesOf(o) map buscar($, cumple))
    case a is Array -> primero(a map buscar($, cumple))
    case s is String -> do {
            var t = trim(s)
            ---
            if ((t startsWith "{") or (t startsWith "[")) do {
                var r = try(() -> read(t, "application/json"))
                ---
                if (r.success) buscar(r.result, cumple) else null
            } else null
        }
    else -> null
}

// Resultado de negocio de la POC: primer objeto con la clave "tipo" de texto
fun resultadoNegocio(v) = buscar(v, (o) -> (o.tipo is String))

// Task A2A: primer objeto con status.state
fun taskA2a(v) = buscar(v, (o) -> (o.status is Object) and (o.status.state != null))

// Textos de las partes de un mensaje A2A
fun textosDe(parts) = ((parts default []) filter ($.text != null) map ($.text as String)) joinBy " "

// Resultado de una tool concreta dentro de la respuesta del conector Inference ([MCP] Tooling).
// El nombre de la tool puede venir con el prefijo de la config MCP (<config>__<tool>).
fun resultadoToolLlm(respuestaLlm, tool: String) = do {
    var informe = (respuestaLlm.toolsExecutionReport default []) filter (((($.tool default "") as String) == tool) or ((($.tool default "") as String) endsWith ("__" ++ tool)))
    ---
    resultadoNegocio(informe map $.result)
}

// Nombres de las tools que el LLM decidió ejecutar (para el log)
fun toolsEjecutadas(respuestaLlm) = (respuestaLlm.toolsExecutionReport default []) map (($.tool default "") as String)

// Euros con dos decimales: 1234.5 -> "1.234,50 €"
// (formato manual para no depender del locale de la JVM)
fun miles(s: String): String = if (sizeOf(s) <= 3) s else (miles(s[0 to sizeOf(s) - 4]) ++ "." ++ s[-3 to -1])
fun eur(x) = if (x == null) "-" else do {
    var centimos = round((x as Number) * 100)
    var entero = floor(centimos / 100)
    var decimales = centimos mod 100
    ---
    miles(entero as String) ++ "," ++ (if (decimales < 10) "0" else "") ++ (decimales as String) ++ " €"
}
