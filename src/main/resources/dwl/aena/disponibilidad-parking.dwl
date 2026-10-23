%dw 2.0
/*
 * Disponibilidad de parking AENA para {aeropuerto, fechaEntrada, fechaSalida} (payload).
 * Devuelve {tipo: "parking_disponibilidad", aeropuerto, fechaEntrada, fechaSalida, dias, opciones[]}
 * o {tipo: "error", codigo, mensaje}.
 */
output application/json
import * from dwl::aena::aeropuertos
import * from dwl::aena::parking
var codigo = codigoAeropuerto(payload.aeropuerto)
var a = aeropuerto(codigo)
var textoAeropuerto = (payload.aeropuerto default "") as String
var entrada = normalizarFecha(payload.fechaEntrada)
var salida = normalizarFecha(payload.fechaSalida)
var dias = diasFacturables(payload.fechaEntrada, payload.fechaSalida)
var cfg = {
    precioDiaGeneral: p('aena.parking.precioDiaGeneral'),
    precioDiaExpress: p('aena.parking.precioDiaExpress'),
    precioDiaLargaEstancia: p('aena.parking.precioDiaLargaEstancia'),
    minDiasLargaEstancia: p('aena.parking.minDiasLargaEstancia')
}
fun fallo(c, m) = {tipo: "error", codigo: c, mensaje: m}
---
if (a == null)
    fallo("AEROPUERTO_DESCONOCIDO", "No conozco el aeropuerto '$(textoAeropuerto)'. Aeropuertos disponibles: $(codigosConocidos)")
else if (not a.aena)
    fallo("AEROPUERTO_NO_AENA", "$(a.nombre) ($(codigo)) no pertenece a la red de AENA: el parking solo se puede reservar en aeropuertos españoles de AENA")
else if (entrada == null or salida == null)
    fallo("FECHA_NO_VALIDA", "Las fechas de entrada y salida deben tener formato AAAA-MM-DD o AAAA-MM-DDTHH:mm")
else if (dias == null)
    fallo("FECHAS_INCOHERENTES", "La fecha de salida del parking debe ser posterior a la de entrada")
else
    {
        tipo: "parking_disponibilidad",
        aeropuerto: infoAeropuerto(codigo),
        fechaEntrada: entrada,
        fechaSalida: salida,
        dias: dias,
        opciones: productos(codigo, dias, cfg)
    }
