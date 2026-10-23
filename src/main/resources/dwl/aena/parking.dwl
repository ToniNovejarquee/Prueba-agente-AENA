%dw 2.0
/*
 * Tarifas del parking del mock de AENA (módulo DataWeave): import * from dwl::aena::parking
 * Las fechas admiten "yyyy-MM-dd" o "yyyy-MM-ddTHH:mm" (hora local del aeropuerto).
 */
import * from dwl::aena::aeropuertos

// "2026-11-20" -> "2026-11-20T00:00"; "2026-11-20T07:15:00" -> "2026-11-20T07:15"
fun normalizarFecha(f) = do {
    var t = trim((f default "") as String)
    ---
    if (t matches /\d{4}-\d{2}-\d{2}/) t ++ "T00:00"
    else if (t matches /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}.*/) t[0 to 15]
    else null
}

fun epochSegundos(f: String): Number = ((f ++ ":00Z") as DateTime) as Number

// Días facturables (por día o fracción, mínimo 1); null si las fechas no son válidas
fun diasFacturables(entrada, salida) = do {
    var e = normalizarFecha(entrada)
    var s = normalizarFecha(salida)
    ---
    if (e == null or s == null) null
    else do {
        var horas = (epochSegundos(s) - epochSegundos(e)) / 3600
        ---
        if (horas <= 0) null else max([1, ceil(horas / 24)])
    }
}

/*
 * Productos de parking disponibles en un aeropuerto AENA.
 * cfg = {precioDiaGeneral, precioDiaExpress, precioDiaLargaEstancia, minDiasLargaEstancia}
 */
fun productos(codigo: String, dias: Number, cfg) = do {
    var a = aeropuerto(codigo)
    var catalogo = [
        {opcionId: "EXPRESS", nombre: "Parking Express $(a.terminal)", descripcion: "Junto a la terminal $(a.terminal), a 2 min a pie", precioDia: cfg.precioDiaExpress as Number},
        {opcionId: "GENERAL", nombre: "Parking General P1", descripcion: "A 8 min a pie de la terminal $(a.terminal)", precioDia: cfg.precioDiaGeneral as Number},
        {opcionId: "LARGA_ESTANCIA", nombre: "Parking Larga Estancia", descripcion: "Con autobús lanzadera gratuito cada 10 min. Mínimo $(cfg.minDiasLargaEstancia) días", precioDia: cfg.precioDiaLargaEstancia as Number, minDias: cfg.minDiasLargaEstancia as Number}
    ]
    ---
    catalogo map ((prod) -> prod ++ {
        dias: dias,
        disponible: dias >= (prod.minDias default 1),
        precioTotal: round(prod.precioDia * dias * 100) / 100,
        moneda: "EUR"
    })
}
