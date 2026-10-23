%dw 2.0
/*
 * Página de pago de la pasarela simulada (mock Sipay). Entrada: vars.pago (o null), vars.idPago.
 * Es solo una simulación: no pide ni guarda datos de tarjeta.
 */
output text/plain
import * from dwl::comun::utilidades
var pg = vars.pago
fun esc(t) = ((t default "") as String) replace "&" with "&amp;" replace "<" with "&lt;" replace ">" with "&gt;" replace "\"" with "&quot;"
var cabecera = "<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
    ++ "<title>Pago seguro</title><style>"
    ++ "body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#f3f5f9;color:#1d2433}"
    ++ ".top{background:#0b2a5b;color:#fff;padding:16px 24px;font-weight:600;letter-spacing:.3px}"
    ++ ".card{max-width:440px;margin:32px auto;background:#fff;border-radius:12px;box-shadow:0 4px 18px rgba(0,0,0,.08);padding:28px}"
    ++ "h1{font-size:20px;margin:0 0 4px}.muted{color:#6b7385;font-size:14px}"
    ++ ".importe{font-size:34px;font-weight:700;margin:18px 0}"
    ++ "dl{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:14px;margin:0 0 20px}dt{color:#6b7385}dd{margin:0}"
    ++ "label{display:block;font-size:13px;color:#6b7385;margin:10px 0 4px}"
    ++ "input{width:100%;box-sizing:border-box;padding:10px;border:1px solid #d5dae3;border-radius:8px;font-size:15px;background:#f8f9fb}"
    ++ ".fila{display:flex;gap:10px}.fila>div{flex:1}"
    ++ "button{width:100%;padding:13px;border:0;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;margin-top:16px}"
    ++ ".pagar{background:#1a7f37;color:#fff}.cancelar{background:transparent;color:#6b7385;margin-top:6px}"
    ++ ".ok{background:#e7f6ec;color:#1a7f37;padding:14px;border-radius:8px}.ko{background:#fdecec;color:#b42318;padding:14px;border-radius:8px}"
    ++ ".aviso{font-size:12px;color:#8a91a1;margin-top:18px;text-align:center}"
    ++ "</style></head><body><div class='top'>" ++ esc(p('aena.pagos.pasarela')) ++ " · Pago seguro</div><div class='card'>"
var pie = "<p class='aviso'>Entorno de demostración: no se realiza ningún cargo real.</p></div></body></html>"
var detalle = if (pg == null) "" else
    "<dl><dt>Concepto</dt><dd>" ++ esc(pg.concepto) ++ "</dd>"
    ++ "<dt>Referencia</dt><dd>" ++ esc(pg.referencia) ++ "</dd>"
    ++ "<dt>Id. de pago</dt><dd>" ++ esc(pg.idPago) ++ "</dd></dl>"
var cuerpo = if (pg == null)
        "<h1>Pago no encontrado</h1><p class='ko'>No existe el pago " ++ esc(vars.idPago) ++ ". Pide a tu asistente un nuevo enlace de pago.</p>"
    else if (pg.estado == "PAGADO")
        "<h1>Pago completado</h1><div class='importe'>" ++ eur(pg.importe) ++ "</div>" ++ detalle
        ++ "<p class='ok'>Pago autorizado (código " ++ esc(pg.codigoAutorizacion) ++ "). Ya puedes cerrar esta ventana y decirle a tu asistente: <b>«ya he pagado»</b>.</p>"
    else if (pg.estado == "CANCELADO")
        "<h1>Pago cancelado</h1>" ++ detalle ++ "<p class='ko'>Has cancelado el pago. Puedes pedir a tu asistente un nuevo enlace de pago.</p>"
    else
        "<h1>Confirma tu pago</h1><div class='muted'>Reserva de viaje</div><div class='importe'>" ++ eur(pg.importe) ++ "</div>" ++ detalle
        ++ "<form method='post'>"
        ++ "<label>Titular de la tarjeta</label><input value='CLIENTE DEMO' readonly>"
        ++ "<label>Número de tarjeta</label><input value='4111 1111 1111 1111' readonly>"
        ++ "<div class='fila'><div><label>Caducidad</label><input value='12/30' readonly></div><div><label>CVV</label><input value='123' readonly></div></div>"
        ++ "<button class='pagar' name='accion' value='pagar'>Pagar " ++ eur(pg.importe) ++ "</button>"
        ++ "<button class='cancelar' name='accion' value='cancelar'>Cancelar</button>"
        ++ "</form>"
---
cabecera ++ cuerpo ++ pie
