%dw 2.0
/*
 * Catálogo de aeropuertos del mock de AENA (módulo DataWeave): import * from dwl::aena::aeropuertos
 *   aena: true  -> aeropuerto de la red de AENA (tiene parking AENA)
 *   tz          -> diferencia horaria con UTC en invierno (aproximación de la POC, sin horario de verano)
 *   alias       -> nombres aceptados además del código IATA (en minúsculas y sin tildes)
 */

var aeropuertos = {
    MAD: {nombre: "Adolfo Suárez Madrid-Barajas", ciudad: "Madrid", pais: "España", aena: true, terminal: "T4", lat: 40.4719, lon: -3.5626, tz: 1, alias: ["madrid", "barajas", "madrid-barajas"]},
    BCN: {nombre: "Josep Tarradellas Barcelona-El Prat", ciudad: "Barcelona", pais: "España", aena: true, terminal: "T1", lat: 41.2971, lon: 2.0785, tz: 1, alias: ["barcelona", "el prat"]},
    AGP: {nombre: "Málaga-Costa del Sol", ciudad: "Málaga", pais: "España", aena: true, terminal: "T3", lat: 36.6749, lon: -4.4991, tz: 1, alias: ["malaga"]},
    PMI: {nombre: "Palma de Mallorca", ciudad: "Palma", pais: "España", aena: true, terminal: "T", lat: 39.5517, lon: 2.7388, tz: 1, alias: ["palma", "mallorca", "palma de mallorca"]},
    SVQ: {nombre: "Sevilla", ciudad: "Sevilla", pais: "España", aena: true, terminal: "T", lat: 37.4180, lon: -5.8931, tz: 1, alias: ["sevilla", "seville"]},
    VLC: {nombre: "Valencia", ciudad: "Valencia", pais: "España", aena: true, terminal: "T", lat: 39.4893, lon: -0.4816, tz: 1, alias: ["valencia"]},
    ALC: {nombre: "Alicante-Elche Miguel Hernández", ciudad: "Alicante", pais: "España", aena: true, terminal: "T", lat: 38.2822, lon: -0.5582, tz: 1, alias: ["alicante", "elche"]},
    BIO: {nombre: "Bilbao", ciudad: "Bilbao", pais: "España", aena: true, terminal: "T", lat: 43.3011, lon: -2.9106, tz: 1, alias: ["bilbao"]},
    LPA: {nombre: "Gran Canaria", ciudad: "Las Palmas de Gran Canaria", pais: "España", aena: true, terminal: "T", lat: 27.9319, lon: -15.3866, tz: 0, alias: ["gran canaria", "las palmas"]},
    TFN: {nombre: "Tenerife Norte-Ciudad de La Laguna", ciudad: "Tenerife", pais: "España", aena: true, terminal: "T", lat: 28.4827, lon: -16.3415, tz: 0, alias: ["tenerife", "tenerife norte"]},
    LHR: {nombre: "Londres Heathrow", ciudad: "Londres", pais: "Reino Unido", aena: false, terminal: "T5", lat: 51.4700, lon: -0.4543, tz: 0, alias: ["londres", "london", "heathrow"]},
    CDG: {nombre: "París-Charles de Gaulle", ciudad: "París", pais: "Francia", aena: false, terminal: "T2", lat: 49.0097, lon: 2.5479, tz: 1, alias: ["paris", "charles de gaulle"]},
    FCO: {nombre: "Roma Fiumicino", ciudad: "Roma", pais: "Italia", aena: false, terminal: "T1", lat: 41.8003, lon: 12.2389, tz: 1, alias: ["roma", "rome", "fiumicino"]},
    AMS: {nombre: "Ámsterdam Schiphol", ciudad: "Ámsterdam", pais: "Países Bajos", aena: false, terminal: "T", lat: 52.3105, lon: 4.7683, tz: 1, alias: ["amsterdam", "schiphol"]},
    LIS: {nombre: "Lisboa Humberto Delgado", ciudad: "Lisboa", pais: "Portugal", aena: false, terminal: "T1", lat: 38.7742, lon: -9.1342, tz: 0, alias: ["lisboa", "lisbon"]},
    FRA: {nombre: "Fráncfort", ciudad: "Fráncfort", pais: "Alemania", aena: false, terminal: "T1", lat: 50.0379, lon: 8.5622, tz: 1, alias: ["francfort", "frankfurt"]},
    JFK: {nombre: "Nueva York John F. Kennedy", ciudad: "Nueva York", pais: "Estados Unidos", aena: false, terminal: "T1", lat: 40.6413, lon: -73.7781, tz: -5, alias: ["nueva york", "new york", "jfk"]}
}

fun sinTildes(s: String): String = lower(s)
    replace /[áàäâ]/ with "a"
    replace /[éèëê]/ with "e"
    replace /[íìïî]/ with "i"
    replace /[óòöô]/ with "o"
    replace /[úùüû]/ with "u"

// Código IATA a partir de un código o de un nombre de ciudad/aeropuerto; null si no se conoce
fun codigoAeropuerto(texto) = do {
    var t = trim((texto default "") as String)
    var codigo = upper(t)
    var nombre = sinTildes(t)
    ---
    if (aeropuertos[codigo] != null) codigo
    else ((keysOf(aeropuertos) map ($ as String)) filter ((k) -> (aeropuertos[k].alias contains nombre)))[0]
}

fun aeropuerto(codigo) = if (codigo == null) null else aeropuertos[codigo as String]

// Resumen del aeropuerto para las respuestas
fun infoAeropuerto(codigo) = do {
    var a = aeropuerto(codigo)
    ---
    if (a == null) null else {codigo: codigo, aeropuerto: a.nombre, ciudad: a.ciudad, pais: a.pais, terminal: a.terminal, redAena: a.aena}
}

var codigosConocidos = (keysOf(aeropuertos) map ($ as String)) joinBy ", "
