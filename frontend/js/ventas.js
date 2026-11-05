"use strict";

/* Debe coincidir con TRANSICIONES_ENVIO de app/services/envios.py */
const TRANSICIONES_ENVIO = {
    PREPARANDO: ["ENVIADO", "PROBLEMA"],
    ENVIADO: ["EN_TRANSITO", "PROBLEMA"],
    EN_TRANSITO: ["ENTREGADO", "PROBLEMA"],
    PROBLEMA: ["PREPARANDO", "ENVIADO"],
    ENTREGADO: [],
    CANCELADO: []
};

const TEXTO_ACCION_ENVIO = {
    ENVIADO: "Marcar como enviado",
    EN_TRANSITO: "Marcar en tránsito",
    ENTREGADO: "Marcar como entregado",
    PROBLEMA: "Reportar novedad",
    PREPARANDO: "Volver a preparando"
};

const TRANSPORTADORAS = ["Servientrega", "Coordinadora", "Interrapidisimo", "Envia", "Deprisa"];

let filtroEstado = "";

/* ------------------------------------------------------------------ */
/* Resumen y lista                                                     */
/* ------------------------------------------------------------------ */

async function cargarResumen() {
    try {
        const r = await api("GET", "/ventas/resumen");
        const porPreparar = r.ventas_por_estado.PENDIENTE + r.ventas_por_estado.PREPARANDO;

        document.getElementById("indicadores").innerHTML = `
            <div class="indicador"><div class="valor">${precio(r.ingresos_netos)}</div><div class="rotulo">Ingresos netos</div></div>
            <div class="indicador"><div class="valor">${r.unidades_vendidas}</div><div class="rotulo">Unidades vendidas</div></div>
            <div class="indicador"><div class="valor">${porPreparar}</div><div class="rotulo">Por despachar</div></div>
            <div class="indicador"><div class="valor">${r.ventas_por_estado.ENTREGADA}</div><div class="rotulo">Entregadas</div></div>`;
    } catch (e) {
        document.getElementById("indicadores").innerHTML = "";
    }
}

async function cargarSolicitudes() {
    const destino = document.getElementById("solicitudes");

    try {
        const solicitudes = await api("GET", "/cancelaciones/?rol=VENDEDOR&estado=SOLICITADA");

        destino.innerHTML = solicitudes.length ? `
            <div class="mensaje mensaje-aviso">
                Tienes ${solicitudes.length} solicitud${solicitudes.length === 1 ? "" : "es"} de cancelación por responder:
                <ul>${solicitudes.map((s) => `
                    <li>Venta #${s.id_venta} (pedido #${s.id_pedido}) · ${precio(s.monto_reembolso)} ·
                        <button type="button" class="boton-texto" data-ver="${s.id_venta}">Responder</button></li>`).join("")}
                </ul>
            </div>` : "";
    } catch (e) {
        destino.innerHTML = "";
    }
}

async function cargarLista() {
    const lista = document.getElementById("lista");

    try {
        const ventas = await api("GET", filtroEstado ? `/ventas/?estado=${filtroEstado}` : "/ventas/");

        if (!ventas.length) {
            lista.innerHTML = `<div class="vacio">${ICONOS.caja}<p>${filtroEstado ? "No hay ventas en este estado." : "Aún no tienes ventas."}</p></div>`;
            return;
        }

        lista.innerHTML = `
            <div class="tabla-envoltura">
                <table class="tabla">
                    <thead>
                        <tr><th>Venta</th><th>Fecha</th><th>Comprador</th><th>Destino</th><th class="numero">Valor</th><th>Estado</th><th>Envío</th><th></th></tr>
                    </thead>
                    <tbody>
                        ${ventas.map((v) => `
                            <tr>
                                <td>#${v.id_venta}<div class="ayuda">Pedido #${v.id_pedido}</div></td>
                                <td>${fecha(v.fecha)}</td>
                                <td>${esc(v.comprador)}</td>
                                <td>${esc(v.ciudad_entrega || "—")}</td>
                                <td class="numero">${precio(v.subtotal_neto)}${v.monto_cancelado > 0 ? `<div class="ayuda">de ${precio(v.subtotal)}</div>` : ""}</td>
                                <td>${etiquetaEstado(v.estado)}</td>
                                <td>${v.envio ? etiquetaEstado(v.envio.estado) : `<span class="ayuda">Sin crear</span>`}</td>
                                <td><button type="button" class="boton boton-chico" data-ver="${v.id_venta}">Gestionar</button></td>
                            </tr>`).join("")}
                    </tbody>
                </table>
            </div>`;
    } catch (e) {
        lista.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
    }
}

function recargarTodo() {
    cargarResumen();
    cargarSolicitudes();
    cargarLista();
}

/* ------------------------------------------------------------------ */
/* Detalle y gestión                                                   */
/* ------------------------------------------------------------------ */

async function abrirVenta(idVenta) {
    const { elemento } = abrirModal({
        titulo: `Venta #${idVenta}`,
        contenido: `<div class="cargando">Cargando...</div>`
    });

    const cuerpo = elemento.querySelector(".modal-cuerpo");

    const recargar = async () => {
        try {
            pintarVenta(cuerpo, await api("GET", `/ventas/${idVenta}`), async () => {
                await recargar();
                recargarTodo();
            });
        } catch (e) {
            cuerpo.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
        }
    };

    await recargar();
}

function pintarVenta(cuerpo, v, alCambiar) {
    const envio = v.envio;
    const solicitud = v.cancelaciones.find((c) => c.estado === "SOLICITADA");
    const bloqueada = ["CANCELADA", "CANCELACION_SOLICITADA"].includes(v.estado) || v.estado_pedido === "CANCELADO";
    const siguientes = envio && !bloqueada ? TRANSICIONES_ENVIO[envio.estado] || [] : [];

    let gestionEnvio = "";

    if (!envio && v.estado === "PENDIENTE" && !bloqueada) {
        gestionEnvio = `
            <form id="form-envio" class="fila fila-2" style="align-items:end">
                <div class="campo" style="margin:0">
                    <label for="transportadora">Transportadora</label>
                    <select class="control" id="transportadora">
                        <option value="">Asignar automáticamente</option>
                        ${TRANSPORTADORAS.map((t) => `<option>${t}</option>`).join("")}
                    </select>
                </div>
                <div><button type="submit" class="boton">Crear envío</button></div>
            </form>`;
    } else if (envio) {
        gestionEnvio = `
            <ul class="lista-datos">
                <li><span>Estado del envío</span><span>${etiquetaEstado(envio.estado)}</span></li>
                <li><span>Transportadora</span><span>${esc(envio.transportadora)}</span></li>
                <li><span>Guía</span><span>${esc(envio.numero_guia)}</span></li>
                <li><span>Despachado</span><span>${fecha(envio.fecha_despacho, true)}</span></li>
                <li><span>Entregado</span><span>${fecha(envio.fecha_entrega, true)}</span></li>
            </ul>
            <div class="grupo-botones">
                ${siguientes.map((s) => `
                    <button type="button" class="boton ${s === "PROBLEMA" ? "boton-secundario" : ""}" data-estado-envio="${s}">${TEXTO_ACCION_ENVIO[s]}</button>`).join("")}
                <button type="button" class="boton boton-secundario" data-seguimiento="${envio.id_envio}">Ver historial</button>
            </div>
            ${v.estado === "CANCELACION_SOLICITADA" ? `<p class="ayuda">El envío no se puede actualizar mientras haya una solicitud de cancelación pendiente.</p>` : ""}`;
    } else {
        gestionEnvio = `<p class="ayuda">Esta venta no requiere envío.</p>`;
    }

    cuerpo.innerHTML = `
        <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:12px">
            <div>${etiquetaEstado(v.estado)} <span class="ayuda" style="display:inline">· Pedido #${v.id_pedido} · ${fecha(v.fecha, true)}</span></div>
            ${ESTADOS_SIN_DESPACHAR.includes(v.estado) && v.estado_pedido !== "CANCELADO"
                ? `<button type="button" class="boton boton-peligro boton-chico" id="cancelar-venta">Cancelar venta</button>` : ""}
        </div>

        ${solicitud ? `
            <div class="mensaje mensaje-aviso">
                <strong>El comprador solicitó cancelar esta venta.</strong><br>
                Motivo: ${esc(solicitud.motivo)}<br>
                Reembolso: ${precio(solicitud.monto_reembolso)}
                <div class="grupo-botones" style="margin-top:10px">
                    <button type="button" class="boton boton-chico" data-responder="aprobar" data-id="${solicitud.id_cancelacion}">Aprobar cancelación</button>
                    <button type="button" class="boton boton-secundario boton-chico" data-responder="rechazar" data-id="${solicitud.id_cancelacion}">Rechazar</button>
                </div>
            </div>` : ""}

        <h3>Entregar a</h3>
        <ul class="lista-datos">
            <li><span>Comprador</span><span>${esc(v.comprador.nombre)}</span></li>
            <li><span>Celular</span><span>${esc(v.comprador.telefono || "—")}</span></li>
            <li><span>Dirección</span><span>${esc(v.entrega.direccion)}</span></li>
            <li><span>Ciudad</span><span>${esc(v.entrega.ciudad)}, ${esc(v.entrega.departamento)}${v.entrega.codigo_postal ? " · CP " + esc(v.entrega.codigo_postal) : ""}</span></li>
        </ul>

        <h3>Productos</h3>
        <div class="tabla-envoltura">
            <table class="tabla">
                <thead><tr><th>Producto</th><th class="numero">Unidades</th><th class="numero">Precio</th><th class="numero">Subtotal</th></tr></thead>
                <tbody>
                    ${v.productos.map((p) => `
                        <tr>
                            <td>${esc(p.nombre)}</td>
                            <td class="numero">${p.cantidad_vigente}${p.cantidad_cancelada ? `<div class="ayuda">${p.cantidad_cancelada} cancelada${p.cantidad_cancelada === 1 ? "" : "s"}</div>` : ""}</td>
                            <td class="numero">${precio(p.precio_unitario)}</td>
                            <td class="numero">${precio(p.precio_unitario * p.cantidad_vigente)}</td>
                        </tr>`).join("")}
                </tbody>
            </table>
        </div>
        <p style="text-align:right;font-weight:700;color:var(--azul)">Total: ${precio(v.subtotal_neto)}</p>

        <h3>Envío</h3>
        ${gestionEnvio}

        ${tablaCancelaciones(v.cancelaciones)}`;

    /* Crear envío */
    const formEnvio = cuerpo.querySelector("#form-envio");
    if (formEnvio) {
        formEnvio.addEventListener("submit", async (e) => {
            e.preventDefault();
            const transportadora = cuerpo.querySelector("#transportadora").value || null;

            await conBoton(formEnvio.querySelector("button"), async () => {
                try {
                    const r = await api("POST", `/envios/ventas/${v.id_venta}`, { cuerpo: { transportadora } });
                    aviso(`Envío creado con ${r.transportadora}. Guía ${r.numero_guia}.`, "exito");
                    await alCambiar();
                } catch (err) {
                    aviso(err.message, "error");
                }
            }, "Creando...");
        });
    }

    /* Cambiar estado del envío */
    cuerpo.querySelectorAll("[data-estado-envio]").forEach((b) =>
        b.addEventListener("click", async () => {
            const estado = b.dataset.estadoEnvio;
            let observacion = null;

            if (estado === "PROBLEMA") {
                observacion = await pedirMotivo({
                    titulo: "Reportar novedad",
                    etiqueta: "Describe la novedad",
                    explicacion: "El comprador podrá ver esta nota en el seguimiento.",
                    textoBoton: "Reportar"
                });
                if (observacion === null) return;
            }

            try {
                await api("PATCH", `/envios/${envio.id_envio}/estado`, { cuerpo: { estado, observacion } });
                aviso(`Envío actualizado: ${textoEstado(estado)}.`, "exito");
                await alCambiar();
            } catch (err) {
                aviso(err.message, "error");
            }
        })
    );

    /* Seguimiento */
    cuerpo.querySelectorAll("[data-seguimiento]").forEach((b) =>
        b.addEventListener("click", () => verSeguimiento(b.dataset.seguimiento))
    );

    /* Responder solicitud */
    cuerpo.querySelectorAll("[data-responder]").forEach((b) =>
        b.addEventListener("click", async () => {
            const aprobar = b.dataset.responder === "aprobar";
            const observacion = await pedirMotivo({
                titulo: aprobar ? "Aprobar cancelación" : "Rechazar cancelación",
                etiqueta: "Mensaje para el comprador",
                explicacion: aprobar
                    ? "Se devolverán las unidades a tu inventario y se registrará el reembolso al comprador."
                    : "La venta seguirá su curso normal.",
                textoBoton: aprobar ? "Aprobar" : "Rechazar",
                opcional: true
            });

            if (observacion === null) return;

            try {
                await api("POST", `/cancelaciones/${b.dataset.id}/${aprobar ? "aprobar" : "rechazar"}`, {
                    cuerpo: { observacion: observacion || null }
                });
                aviso(aprobar ? "Cancelación aprobada." : "Solicitud rechazada.", "exito");
                await alCambiar();
            } catch (err) {
                aviso(err.message, "error");
            }
        })
    );

    /* Cancelar la venta (vendedor, antes de despachar) */
    const cancelar = cuerpo.querySelector("#cancelar-venta");
    if (cancelar) {
        cancelar.addEventListener("click", async () => {
            const motivo = await pedirMotivo({
                titulo: "Cancelar venta",
                explicacion: "Úsalo si no puedes cumplir con el pedido. El comprador recibirá el reembolso y las unidades volverán a tu inventario.",
                textoBoton: "Cancelar venta"
            });

            if (motivo === null) return;

            try {
                await api("POST", `/cancelaciones/ventas/${v.id_venta}`, { cuerpo: { motivo } });
                aviso("Venta cancelada.", "exito");
                await alCambiar();
            } catch (err) {
                aviso(err.message, "error");
            }
        });
    }
}

/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
    if (!requerirSesion()) return;

    document.getElementById("filtros").addEventListener("click", (e) => {
        const chip = e.target.closest(".chip");
        if (!chip) return;

        document.querySelectorAll("#filtros .chip").forEach((c) => c.classList.remove("activo"));
        chip.classList.add("activo");
        filtroEstado = chip.dataset.estado;
        cargarLista();
    });

    document.querySelector("main").addEventListener("click", (e) => {
        const boton = e.target.closest("[data-ver]");
        if (boton) abrirVenta(Number(boton.dataset.ver));
    });

    recargarTodo();
});
