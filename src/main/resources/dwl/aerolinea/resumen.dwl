%dw 2.0
/*
 * Resumen legible del resultado de una acción del agente de la aerolínea (texto que llega a Copilot).
 * Entrada: vars.accion, vars.resultado ({tipo: "vuelos" | "parking_disponibilidad" | "reserva" | "error", ...}).
 * Incluye siempre el "siguiente paso" para que el asistente sepa cómo seguir la conversación.
 */
output application/java
import * from dwl::comun::utilidades
var r = vars.resultado default {}
var a = vars.accion
fun txt(x) = (x default "") as String
fun hora(s) = if (s == null) "" else (s as String)[11 to 15]
fun dia(s) = if (s == null) "" else (s as String)[0 to 9]
fun lineaVuelo(v, i) =
    "$(i + 1). $(txt(v.numeroVuelo)) · sale $(dia(v.salida)) $(hora(v.salida)) de $(txt(v.origen.codigo)) (terminal $(txt(v.origen.terminal))) · llega $(hora(v.llegada)) a $(txt(v.destino.codigo)) · $(txt(v.duracion)) · $(eur(v.precioPorPasajero)) por pasajero (total $(eur(v.precioTotal)))"
    ++ (if (v.disponible default false) "" else " · SIN PLAZAS SUFICIENTES")
    ++ " · vueloId: $(txt(v.vueloId))"
fun lineaParking(o) =
    "- $(txt(o.opcionId)) · $(txt(o.nombre)): $(txt(o.descripcion)). $(eur(o.precioDia))/día, total $(eur(o.precioTotal)) por $(txt(o.dias)) días"
    ++ (if (o.disponible default false) "" else " (NO DISPONIBLE para estas fechas)")
fun textoPago(pg) =
    if (pg == null) "Pago: pendiente de iniciar."
    else if (pg.estado == "PAGADO") "Pago: PAGADO el $(txt(pg.pagadoEn)) (autorización $(txt(pg.codigoAutorizacion)), id $(txt(pg.idPago)))."
    else if (pg.estado == "CANCELADO") "Pago: CANCELADO por el cliente (id $(txt(pg.idPago)))."
    else "Pago: PENDIENTE. Enlace de pago: $(txt(pg.urlPago))"
fun textoReserva(x) = do {
    var v = x.vuelo default {}
    var pk = x.parking
    ---
    "Reserva $(txt(x.localizador)) · estado $(txt(x.estado))\n"
    ++ "Vuelo $(txt(v.numeroVuelo)): $(txt(v.origen.ciudad)) ($(txt(v.origen.codigo)), terminal $(txt(v.origen.terminal))) → $(txt(v.destino.ciudad)) ($(txt(v.destino.codigo))), sale el $(dia(v.salida)) a las $(hora(v.salida)) y llega a las $(hora(v.llegada)).\n"
    ++ "Titular: $(txt(x.titular.nombre)) $(txt(x.titular.apellidos)) ($(txt(x.titular.email))) · $(txt(x.pasajeros)) pasajero(s) · vuelo $(eur(x.importes.vuelo))\n"
    ++ (if (pk != null) "Parking AENA $(txt(pk.codigoReserva)): $(txt(pk.producto.nombre)) en $(txt(pk.aeropuerto.codigo)), del $(txt(pk.fechaEntrada)) al $(txt(pk.fechaSalida)) ($(txt(pk.dias)) días) · $(eur(pk.importe))\n" else "")
    ++ "TOTAL: $(eur(x.importes.total))\n"
    ++ textoPago(x.pago)
}
fun siguientePaso(x) =
    if (x.estado == "CONFIRMADA") "La reserva está pagada y confirmada. ¡Buen viaje!"
    else if (x.pago.estado == "PENDIENTE") "Siguiente paso: el cliente debe abrir el enlace de pago y pagar; después, usa consultar_reserva con el localizador para confirmar el pago."
    else if (x.pago.estado == "CANCELADO") "El pago se canceló. Si el cliente quiere, usa pagar_reserva para generar un enlace nuevo."
    else if (x.parking == null) "Siguiente paso: ofrece parking de AENA en el aeropuerto de salida (buscar_parking con el localizador y la fecha de recogida del coche) o pasa al pago (pagar_reserva)."
    else "Siguiente paso: pagar la reserva con pagar_reserva."
---
if (r.tipo == "error")
    "No se ha podido completar la operación ($(txt(r.codigo))): $(txt(r.mensaje))"
else if (r.tipo == "vuelos")
    "Vuelos de $(txt(r.origen.ciudad)) ($(txt(r.origen.codigo))) a $(txt(r.destino.ciudad)) ($(txt(r.destino.codigo))) el $(txt(r.fecha)) para $(txt(r.pasajeros)) pasajero(s):\n"
    ++ ((r.vuelos default []) map ((v, i) -> lineaVuelo(v, i)) joinBy "\n")
    ++ "\nSiguiente paso: cuando el cliente elija vuelo, usa reservar_vuelo con su vueloId, el número de pasajeros y el nombre, apellidos y email del titular."
else if (r.tipo == "parking_disponibilidad")
    "Parking AENA en $(txt(r.aeropuerto.aeropuerto)) ($(txt(r.aeropuerto.codigo))) del $(txt(r.fechaEntrada)) al $(txt(r.fechaSalida)):\n"
    ++ ((r.opciones default []) map lineaParking($) joinBy "\n")
    ++ "\nSiguiente paso: cuando el cliente elija, usa reservar_parking con el localizador, el opcionId y las mismas fechas (la matrícula es opcional)."
else if (r.tipo == "reserva")
    (if (a == "pagar_reserva" and r.estado == "CONFIRMADA") "Esta reserva ya estaba pagada.\n" else "")
    ++ textoReserva(r) ++ "\n" ++ siguientePaso(r)
else
    "Operación $(txt(a)) completada (resultado de tipo $(txt(r.tipo)))."
