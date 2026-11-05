"use strict";

const ESTADOS_PEDIDO_CANCELABLES = ["PAGADO", "EN_PROCESO", "PARCIALMENTE_ENVIADO"];

let filtroEstado = "";

/* ------------------------------------------------------------------ */
/* Lista de pedidos                                                    */
/* ------------------------------------------------------------------ */

async function cargarLista() {
    const lista = document.getElementById("lista");
    lista.innerHTML = `<div class="cargando">Cargando pedidos...</div>`;

    try {
        const ruta = filtroEstado ? `/pedidos/?estado=${filtroEstado}` : "/pedidos/";
        const pedidos = await api("GET", ruta);

        if (!pedidos.length) {
            lista.innerHTML = `
                <div class="tarjeta vacio">${ICONOS.caja}
                    <p>${filtroEstado ? "No tienes pedidos en este estado." : "Aún no has hecho compras."}</p>
                    <a class="boton" href="index.html">Ir a la tienda</a>
                </div>`;
            return;
        }

        lista.innerHTML = pedidos.map((p) => `
            <article class="tarjeta-pedido">
                <div>
                    <h3>Pedido #${p.id_pedido} ${etiquetaEstado(p.estado)}</h3>
                    <div class="meta">
                        ${fecha(p.fecha)} · ${p.unidades} unidad${p.unidades === 1 ? "" : "es"} ·
                        Entrega en ${esc(p.ciudad_entrega || "—")} ·
                        Pago ${esc(textoEstado(p.estado_pago || "—").toLowerCase())}
                    </div>
                    <div style="margin-top:6px">
                        <strong style="color:var(--azul)">${precio(p.estado_pago === "APROBADO" ? p.total_neto : p.total)}</strong>
                        ${p.total_cancelado > 0 ? `<span class="ayuda" style="display:inline"> · ${precio(p.total_cancelado)} reembolsado</span>` : ""}
                    </div>
                </div>
                <button type="button" class="boton boton-secundario" data-ver="${p.id_pedido}">Ver detalle</button>
            </article>`).join("");

    } catch (e) {
        lista.innerHTML = `<div class="tarjeta vacio">${esc(e.message)}</div>`;
    }
}

/* ------------------------------------------------------------------ */
/* Detalle del pedido                                                  */
/* ------------------------------------------------------------------ */

function bloqueVenta(venta, productos) {
    const envio = venta.envio;
    let acciones = "";

    if (ESTADOS_SIN_DESPACHAR.includes(venta.estado)) {
        acciones = `<button type="button" class="boton boton-secundario boton-chico" data-cancelar-venta="${venta.id_venta}">Cancelar esta parte</button>`;
    } else if (venta.estado === "ENVIADA") {
        acciones = `<button type="button" class="boton boton-secundario boton-chico" data-solicitar="${venta.id_venta}">Solicitar cancelación</button>`;
    } else if (venta.estado === "CANCELACION_SOLICITADA") {
        acciones = `<span class="ayuda">Esperando respuesta del vendedor.</span>`;
    }

    return `
        <div class="tarjeta" style="border:1px solid var(--borde);box-shadow:none;margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center">
                <div>
                    <strong>Vendedor: ${esc(venta.vendedor)}</strong> ${etiquetaEstado(venta.estado)}
                    <div class="ayuda">
                        ${envio
                            ? `Envío ${esc(textoEstado(envio.estado).toLowerCase())} · ${esc(envio.transportadora)} · Guía ${esc(envio.numero_guia)}`
                            : venta.estado === "CANCELADA" ? "Sin envío" : "El vendedor aún no ha creado el envío."}
                    </div>
                </div>
                <div class="grupo-botones">
                    ${envio ? `<button type="button" class="boton boton-chico" data-seguimiento="${envio.id_envio}">Seguimiento</button>` : ""}
                    ${acciones}
                </div>
            </div>
            <div class="tabla-envoltura" style="margin-top:10px">
                <table class="tabla">
                    <tbody>
                        ${productos.map((p) => `
                            <tr>
                                <td style="width:64px"><div class="miniatura">${imagenProducto(p.imagen_principal, p.nombre)}</div></td>
                                <td>
                                    <a href="producto.html?id=${p.id_producto}">${esc(p.nombre)}</a>
                                    <div class="ayuda">${precio(p.precio_unitario)} c/u</div>
                                </td>
                                <td class="numero">
                                    ${p.cantidad_cancelada
                                        ? `${p.cantidad_vigente} de ${p.cantidad} und.<div class="ayuda">${p.cantidad_cancelada} cancelada${p.cantidad_cancelada === 1 ? "" : "s"}</div>`
                                        : `${p.cantidad} und.`}
                                </td>
                                <td class="numero">${precio(p.precio_unitario * p.cantidad_vigente)}</td>
                            </tr>`).join("")}
                    </tbody>
                </table>
            </div>
        </div>`;
}

async function abrirDetalle(idPedido) {
    const { elemento, cerrar } = abrirModal({
        titulo: `Pedido #${idPedido}`,
        contenido: `<div class="cargando">Cargando...</div>`
    });

    const cuerpo = elemento.querySelector(".modal-cuerpo");

    async function recargar() {
        try {
            const pedido = await api("GET", `/pedidos/${idPedido}`);
            pintarDetalle(cuerpo, pedido, recargar);
        } catch (e) {
            cuerpo.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
        }
    }

    elemento.addEventListener("pedido-cambio", () => {
        recargar();
        cargarLista();
    });

    await recargar();
    return cerrar;
}

function pintarDetalle(cuerpo, pedido, recargar) {
    const pago = pedido.pagos[pedido.pagos.length - 1];
    const hayEntregas = pedido.ventas.some((v) => v.estado === "ENTREGADA");
    const cancelablePedido = ESTADOS_PEDIDO_CANCELABLES.includes(pedido.estado) && !hayEntregas;

    const productosCancelables = pedido.productos.filter((p) => {
        const venta = pedido.ventas.find((v) => v.id_venta === p.id_venta);
        return venta && ESTADOS_SIN_DESPACHAR.includes(venta.estado) && p.cantidad_vigente > 0;
    });

    cuerpo.innerHTML = `
        <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:14px">
            <div>${etiquetaEstado(pedido.estado)} <span class="ayuda" style="display:inline">· ${fecha(pedido.fecha, true)}</span></div>
            <div class="grupo-botones">
                ${productosCancelables.length && ESTADOS_PEDIDO_CANCELABLES.includes(pedido.estado)
                    ? `<button type="button" class="boton boton-secundario boton-chico" id="cancelar-parcial">Cancelar algunos productos</button>` : ""}
                ${cancelablePedido
                    ? `<button type="button" class="boton boton-peligro boton-chico" id="cancelar-total">Cancelar pedido</button>` : ""}
            </div>
        </div>

        <ul class="lista-datos">
            <li><span>Entrega</span><span>${esc(pedido.entrega.direccion)}, ${esc(pedido.entrega.ciudad)}, ${esc(pedido.entrega.departamento)}</span></li>
            <li><span>Pago</span><span>${pago ? `${esc(METODOS_PAGO[pago.metodo] || pago.metodo)} · ${etiquetaEstado(pago.estado)} · Ref. ${esc(pago.referencia)}` : "—"}</span></li>
            <li><span>Total</span><span>${precio(pedido.total)}</span></li>
            ${pedido.total_cancelado > 0 ? `
                <li><span>Reembolsado (simulado)</span><span>− ${precio(pedido.total_cancelado)}</span></li>
                <li><span><strong>Total final</strong></span><span><strong>${precio(pedido.total_neto)}</strong></span></li>` : ""}
        </ul>

        ${pago && pago.estado === "RECHAZADO" ? `
            <div class="mensaje mensaje-error">El pago de este pedido fue rechazado, por eso se canceló. Tus productos siguen en el carrito.</div>` : ""}

        <h3>Productos y envíos</h3>
        ${pedido.ventas.length
            ? pedido.ventas.map((v) => bloqueVenta(v, pedido.productos.filter((p) => p.id_venta === v.id_venta))).join("")
            : `<div class="tabla-envoltura"><table class="tabla"><tbody>
                ${pedido.productos.map((p) => `<tr><td>${esc(p.nombre)}</td><td class="numero">${p.cantidad} und.</td><td class="numero">${precio(p.subtotal)}</td></tr>`).join("")}
               </tbody></table></div>`}

        ${tablaCancelaciones(pedido.cancelaciones)}

        <h3>Historial</h3>
        <button type="button" class="boton-texto" id="ver-historial">Ver historial de estados</button>
        <div id="historial"></div>`;

    const avisarCambio = () => cuerpo.closest(".modal").dispatchEvent(new Event("pedido-cambio"));

    // Seguimiento
    cuerpo.querySelectorAll("[data-seguimiento]").forEach((b) =>
        b.addEventListener("click", () => verSeguimiento(b.dataset.seguimiento))
    );

    // Cancelar o solicitar cancelación de una venta
    cuerpo.querySelectorAll("[data-cancelar-venta], [data-solicitar]").forEach((b) =>
        b.addEventListener("click", async () => {
            const solicitar = Boolean(b.dataset.solicitar);
            const idVenta = b.dataset.solicitar || b.dataset.cancelarVenta;

            const motivo = await pedirMotivo({
                titulo: solicitar ? "Solicitar cancelación" : "Cancelar productos de este vendedor",
                explicacion: solicitar
                    ? "Este envío ya salió. El vendedor revisará tu solicitud y, si la aprueba, recibirás el reembolso."
                    : "Se cancelarán todas las unidades de este vendedor y se te reembolsará su valor.",
                textoBoton: solicitar ? "Enviar solicitud" : "Cancelar productos"
            });

            if (motivo === null) return;

            try {
                const r = await api("POST", `/cancelaciones/ventas/${idVenta}`, { cuerpo: { motivo } });
                aviso(r.estado === "SOLICITADA" ? "Solicitud enviada al vendedor." : `Cancelación aplicada. Reembolso: ${precio(r.monto_reembolso)}.`, "exito");
                avisarCambio();
            } catch (e) {
                aviso(e.message, "error");
            }
        })
    );

    // Cancelar todo el pedido
    const botonTotal = cuerpo.querySelector("#cancelar-total");
    if (botonTotal) {
        botonTotal.addEventListener("click", async () => {
            const motivo = await pedirMotivo({
                titulo: "Cancelar pedido completo",
                explicacion: "Las partes que aún no se han despachado se cancelan de inmediato. Las que ya están en camino quedan como solicitud para el vendedor.",
                textoBoton: "Cancelar pedido"
            });

            if (motivo === null) return;

            try {
                const r = await api("POST", `/cancelaciones/pedidos/${pedido.id_pedido}/total`, { cuerpo: { motivo } });
                const solicitudes = r.cancelaciones.filter((c) => c.estado === "SOLICITADA").length;
                aviso(
                    solicitudes
                        ? `Cancelación procesada. ${solicitudes} parte(s) ya despachada(s) quedan pendientes de aprobación.`
                        : `Pedido cancelado. Reembolso: ${precio(r.monto_reembolsado)}.`,
                    "exito"
                );
                avisarCambio();
            } catch (e) {
                aviso(e.message, "error");
            }
        });
    }

    // Cancelación parcial
    const botonParcial = cuerpo.querySelector("#cancelar-parcial");
    if (botonParcial) {
        botonParcial.addEventListener("click", () => abrirCancelacionParcial(pedido, productosCancelables, avisarCambio));
    }

    // Historial
    cuerpo.querySelector("#ver-historial").addEventListener("click", async (e) => {
        e.target.remove();
        const destino = cuerpo.querySelector("#historial");
        destino.innerHTML = `<div class="cargando">Cargando...</div>`;

        try {
            const h = await api("GET", `/pedidos/${pedido.id_pedido}/historial`);
            destino.innerHTML = h.historial.length ? `
                <ol class="linea-tiempo">
                    ${h.historial.map((x) => `
                        <li>
                            <strong>${x.tipo === "PEDIDO" ? "Pedido" : "Venta #" + x.id_operacion}: ${esc(textoEstado(x.estado_nuevo))}</strong>
                            <div class="fecha">${fecha(x.fecha, true)}</div>
                            ${x.observacion ? `<div>${esc(x.observacion)}</div>` : ""}
                        </li>`).join("")}
                </ol>` : `<p class="ayuda">Sin movimientos.</p>`;
        } catch (err) {
            destino.innerHTML = `<div class="mensaje mensaje-error">${esc(err.message)}</div>`;
        }
    });
}

function abrirCancelacionParcial(pedido, productos, alTerminar) {
    const { elemento, cerrar } = abrirModal({
        titulo: "Cancelar algunos productos",
        contenido: `
            <form id="form-parcial" novalidate>
                <p style="margin-top:0">Marca los productos y las unidades que quieres cancelar. Solo aparecen los que aún no se han despachado.</p>
                <div id="msg-parcial"></div>
                <div class="tabla-envoltura">
                    <table class="tabla">
                        <thead><tr><th></th><th>Producto</th><th class="numero">Vigentes</th><th class="numero">A cancelar</th></tr></thead>
                        <tbody>
                            ${productos.map((p) => `
                                <tr>
                                    <td><input type="checkbox" data-producto="${p.id_producto}" aria-label="Cancelar ${esc(p.nombre)}"></td>
                                    <td>${esc(p.nombre)}<div class="ayuda">${esc(p.vendedor)} · ${precio(p.precio_unitario)} c/u</div></td>
                                    <td class="numero">${p.cantidad_vigente}</td>
                                    <td class="numero">
                                        <input type="number" class="control" style="width:80px" min="1" max="${p.cantidad_vigente}"
                                               value="${p.cantidad_vigente}" data-cantidad="${p.id_producto}" disabled>
                                    </td>
                                </tr>`).join("")}
                        </tbody>
                    </table>
                </div>
                <div class="campo" style="margin-top:14px">
                    <label for="motivo-parcial">Motivo</label>
                    <textarea class="control" id="motivo-parcial" maxlength="500" placeholder="Cuéntanos por qué cancelas"></textarea>
                </div>
                <div class="linea" style="display:flex;justify-content:space-between;font-weight:700;color:var(--azul)">
                    <span>Reembolso estimado</span><span id="reembolso">${precio(0)}</span>
                </div>
                <div class="grupo-botones" style="justify-content:flex-end;margin-top:14px">
                    <button type="button" class="boton boton-secundario" data-cerrar>Volver</button>
                    <button type="submit" class="boton boton-peligro">Cancelar seleccionados</button>
                </div>
            </form>`
    });

    const form = elemento.querySelector("#form-parcial");
    elemento.querySelector("[data-cerrar]").addEventListener("click", cerrar);

    const calcular = () => {
        let total = 0;
        productos.forEach((p) => {
            const marcado = form.querySelector(`[data-producto="${p.id_producto}"]`).checked;
            const entrada = form.querySelector(`[data-cantidad="${p.id_producto}"]`);
            entrada.disabled = !marcado;
            if (marcado) total += p.precio_unitario * Math.min(p.cantidad_vigente, Math.max(0, Number(entrada.value) || 0));
        });
        form.querySelector("#reembolso").textContent = precio(total);
    };

    form.addEventListener("input", calcular);
    form.addEventListener("change", calcular);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const caja = form.querySelector("#msg-parcial");
        const motivo = form.querySelector("#motivo-parcial").value.trim();
        const seleccion = [];
        const errores = [];

        productos.forEach((p) => {
            if (!form.querySelector(`[data-producto="${p.id_producto}"]`).checked) return;

            const cantidad = Math.floor(Number(form.querySelector(`[data-cantidad="${p.id_producto}"]`).value));
            if (!cantidad || cantidad < 1 || cantidad > p.cantidad_vigente) {
                errores.push(`${p.nombre}: la cantidad debe estar entre 1 y ${p.cantidad_vigente}.`);
            }
            seleccion.push({ id_producto: p.id_producto, cantidad });
        });

        if (!seleccion.length) errores.push("Marca al menos un producto.");
        if (motivo.length < 5) errores.push("Escribe el motivo (mínimo 5 caracteres).");

        if (errores.length) {
            mostrarMensaje(caja, "Revisa la cancelación:", "error", errores);
            return;
        }

        await conBoton(form.querySelector("[type=submit]"), async () => {
            try {
                const r = await api("POST", `/cancelaciones/pedidos/${pedido.id_pedido}/parcial`, {
                    cuerpo: { motivo, productos: seleccion }
                });
                cerrar();
                aviso(`Cancelación aplicada. Reembolso: ${precio(r.monto_reembolsado)}.`, "exito");
                alTerminar();
            } catch (err) {
                mostrarMensaje(caja, err.message, "error");
            }
        }, "Cancelando...");
    });
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

    document.getElementById("lista").addEventListener("click", (e) => {
        const boton = e.target.closest("[data-ver]");
        if (boton) abrirDetalle(Number(boton.dataset.ver));
    });

    cargarLista();

    const inicial = Number(parametro("pedido"));
    if (inicial) abrirDetalle(inicial);
});
