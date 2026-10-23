%dw 2.0
/*
 * Generador determinista de vuelos del mock de AENA (módulo DataWeave): import * from dwl::aena::vuelos
 *
 * No hay base de datos: para una ruta y una fecha siempre se generan los mismos vuelos, así que
 * consultar_vuelo puede reconstruir un vuelo a partir de su vueloId (DA1234_MADLHR_20261120).
 * Distancia: aproximación equirrectangular (coseno por serie de Taylor; DataWeave no tiene trigonometría).
 * Duración: distancia / 780 km/h + 35 min de rodaje, redondeada a 5 min.
 */
import * from dw::core::Strings
import * from dw::core::Periods
import * from dwl::aena::aeropuertos

var PI = 3.141592653589793

fun rad(g) = (g as Number) * PI / 180
fun cosAprox(x) = 1 - pow(x, 2) / 2 + pow(x, 4) / 24 - pow(x, 6) / 720 + pow(x, 8) / 40320

fun distanciaKm(a, b) = do {
    var dx = rad(b.lon - a.lon) * cosAprox(rad((a.lat + b.lat) / 2))
    var dy = rad(b.lat - a.lat)
    ---
    round(6371 * sqrt(dx * dx + dy * dy))
}

// Semilla numérica estable a partir de un texto
fun semilla(s: String): Number = sum((0 to sizeOf(s) - 1) map ((i) -> charCodeAt(s, i) * (i + 1)))

fun textoDuracion(m: Number) = "$(floor(m / 60)) h $(m mod 60) min"

// Salidas del día: 4 en corto/medio radio, 2 en largo radio
fun horarios(dist: Number) = if (dist > 3000) ["11:15", "16:40"] else ["07:10", "10:35", "14:50", "19:25"]
var factoresPrecio = [1.15, 0.92, 1.0, 1.08]

/*
 * Vuelos de origen a destino en una fecha (yyyy-MM-dd) para un número de pasajeros.
 * cfg = {compania, nombreCompania, precioBase, precioKm, plazasMaximas}
 */
fun generarVuelos(origen: String, destino: String, fecha: String, pasajeros: Number, cfg) = do {
    var a = aeropuerto(origen)
    var b = aeropuerto(destino)
    var dist = distanciaKm(a, b)
    var duracion = round((dist / 780 * 60 + 35) / 5) * 5
    var difHoraria = (b.tz - a.tz) * 60
    var s = semilla(origen ++ destino ++ fecha)
    var fechaCompacta = fecha replace "-" with ""
    ---
    horarios(dist) map ((hora, i) -> do {
        var desplazamiento = ((s + i) mod 4) * 5
        var salida = ((fecha ++ "T" ++ hora ++ ":00") as LocalDateTime) + minutes(desplazamiento)
        var llegada = salida + minutes(duracion + difHoraria)
        var numero = 1000 + ((s + i * 137) mod 8000)
        var plazasLibres = 1 + ((s + i * 3) mod ((cfg.plazasMaximas as Number) default 9))
        var precioBruto = ((cfg.precioBase as Number) + dist * (cfg.precioKm as Number)) * (factoresPrecio[i] default 1) + ((s + i) mod 7)
        var precioPasajero = floor(precioBruto) + 0.99
        ---
        {
            vueloId: "$(cfg.compania)$(numero)_$(origen)$(destino)_$(fechaCompacta)",
            numeroVuelo: "$(cfg.compania) $(numero)",
            compania: cfg.nombreCompania,
            origen: infoAeropuerto(origen),
            destino: infoAeropuerto(destino),
            salida: salida as String {format: "yyyy-MM-dd'T'HH:mm"},
            llegada: llegada as String {format: "yyyy-MM-dd'T'HH:mm"},
            duracionMin: duracion,
            duracion: textoDuracion(duracion),
            distanciaKm: dist,
            escalas: 0,
            tarifa: "Turista (equipaje de mano incluido)",
            plazasLibres: plazasLibres,
            disponible: plazasLibres >= pasajeros,
            pasajeros: pasajeros,
            precioPorPasajero: precioPasajero,
            precioTotal: round(precioPasajero * pasajeros * 100) / 100,
            moneda: "EUR"
        }
    })
}

// Descompone un vueloId (DA1234_MADLHR_20261120) en {origen, destino, fecha}; null si no es válido
fun parsearVueloId(vueloId) = do {
    var partes = ((vueloId default "") as String) splitBy "_"
    ---
    if ((sizeOf(partes) == 3) and (sizeOf(partes[1]) == 6) and (partes[2] matches /\d{8}/))
        {
            origen: partes[1][0 to 2],
            destino: partes[1][3 to 5],
            fecha: partes[2][0 to 3] ++ "-" ++ partes[2][4 to 5] ++ "-" ++ partes[2][6 to 7]
        }
    else null
}
