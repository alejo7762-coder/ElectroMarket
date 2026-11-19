"use strict";

const ESTADOS_PEDIDO_CANCELABLES = ["PAGADO", "EN_PROCESO", "PARCIALMENTE_ENVIADO"];

let filtroEstado = "";
let resenasDelPedido = {};   // "idVenta-idProducto" -> reseña del comprador
let devolucionesDelPedido = [];
let recargarDetalle = null;  // recarga el detalle abierto (lo usa devoluciones.js)

function alCambiarDevolucion() {
    if (recargarDetalle) recargarDetalle();
    cargarLista();
}

/* ------------------------------------------------------------------ */
/* Lista de pedidos                                                    */
/* ------------------------------------------------------------------ */

async function cargarLista() {
    cargarReembolsos();
    cargarDevoluciones();
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
                    <div class="u-mt-6">
                        <strong class="u-tinta">${precio(["APROBADO", "REEMBOLSO_PARCIAL", "REEMBOLSADO"].includes(p.estado_pago) ? p.total_neto : p.total)}</strong>
                        ${p.total_cancelado > 0 ? `<span class="ayuda u-en-linea"> · ${precio(p.total_cancelado)} cancelado</span>` : ""}
                    </div>
                </div>
                <button type="button" class="boton boton-secundario" data-ver="${p.id_pedido}">Ver detalle</button>
            </article>`).join("");

    } catch (e) {
        lista.innerHTML = `<div class="tarjeta vacio">${esc(e.message)}</div>`;
    }
}

/* ------------------------------------------------------------------ */
/* Reembolsos                                                          */
/* ------------------------------------------------------------------ */

function lineaTiempoReembolso(r) {
    const procesado = r.estado === "PROCESADO";
    return `
        <ol class="linea-reembolso" aria-label="Progreso del reembolso">
            <li class="hecho"><strong>${icono("check")}${r.origen === "DEVOLUCION" ? "Devolución recibida" : "Cancelación aprobada"}</strong><span>${fecha(r.fecha_solicitud, true)}</span></li>
            <li class="hecho"><strong>${icono("reembolso")}Reembolso registrado</strong><span>${esc(METODOS_PAGO[r.metodo_destino] || r.metodo_destino)}</span></li>
            <li class="${procesado ? "hecho" : "actual"}"><strong>${icono(procesado ? "billetera" : "historial")}${procesado ? "Dinero devuelto" : "En proceso"}</strong>
                <span>${procesado ? `${fecha(r.fecha_procesado, true)} · ${esc(r.referencia)}` : "La pasarela lo procesa en pocos minutos"}</span></li>
        </ol>`;
}

function tablaReembolsos(reembolsos) {
    return `
        <div class="lista-reembolsos">
            ${reembolsos.map((r) => `
                <article class="tarjeta-reembolso">
                    <div class="tarjeta-reembolso-cabecera">
                        <div>
                            <strong>Pedido #${r.id_pedido}</strong>
                            <span class="ayuda u-en-linea"> · ${r.origen === "DEVOLUCION" ? `Devolución #${r.id_devolucion}` : `Cancelación ${r.tipo_cancelacion === "TOTAL" ? "total" : "parcial"} #${r.id_cancelacion}`}</span>
                        </div>
                        <div class="monto-reembolso">${precio(r.valor)} ${etiquetaEstado(r.estado === "PENDIENTE" ? "PENDIENTE" : r.estado)}</div>
                    </div>
                    ${r.motivo ? `<p class="ayuda">Motivo: ${esc(r.motivo)}</p>` : ""}
                    ${lineaTiempoReembolso(r)}
                </article>`).join("")}
        </div>`;
}

async function cargarDevoluciones() {
    const destino = document.getElementById("devoluciones");
    if (!destino) return;
    try {
        const devoluciones = await api("GET", "/devoluciones/?rol=COMPRADOR");
        destino.innerHTML = devoluciones.length
            ? devoluciones.map((d) => tarjetaDevolucion(d, { mostrarPedido: true })).join("")
            : `<div class="tarjeta vacio"><p>No tienes devoluciones. Cuando solicites una, aquí verás su estado y lo que sigue.</p></div>`;
    } catch (e) {
        destino.innerHTML = `<div class="mensaje mensaje-error">No se pudieron cargar las devoluciones: ${esc(e.message)}</div>`;
    }
}

async function cargarReembolsos() {
    const destino = document.getElementById("reembolsos");
    if (!destino) return;

    try {
        const datos = await api("GET", "/reembolsos/");

        if (!datos.total) {
            destino.innerHTML = `<div class="tarjeta vacio"><p>No tienes reembolsos. Si cancelas un pedido, aquí verás la devolución de tu dinero.</p></div>`;
            return;
        }

        destino.innerHTML = `
            <div class="resumen-reembolsos">
                <div><span>Devuelto</span><strong>${precio(datos.total_reembolsado)}</strong></div>
                <div><span>En proceso</span><strong>${precio(datos.total_pendiente)}</strong></div>
                <div><span>Reembolsos</span><strong>${datos.total}</strong></div>
            </div>
            ${tablaReembolsos(datos.reembolsos)}`;
    } catch (e) {
        destino.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
    }
}

async function cargarReembolsosPedido(idPedido) {
    const destino = document.getElementById("reembolsos-pedido");
    if (!destino) return;

    try {
        const datos = await api("GET", `/reembolsos/?id_pedido=${idPedido}`);
        destino.innerHTML = datos.total
            ? `<h3>Reembolsos</h3>${tablaReembolsos(datos.reembolsos)}`
            : "";
    } catch (e) {
        destino.innerHTML = "";
    }
}

/* ------------------------------------------------------------------ */
/* Detalle del pedido                                                  */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/* Reseñas de productos entregados                                     */
/* ------------------------------------------------------------------ */

function botonResena(venta, p) {
    const r = resenasDelPedido[`${venta.id_venta}-${p.id_producto}`];
    const datos = `data-resenar="${venta.id_venta}" data-producto="${p.id_producto}" data-nombre="${esc(p.nombre)}"`;
    return r
        ? `${estrellas(r.calificacion_producto)}<button type="button" class="boton-texto" ${datos}>Editar reseña</button>`
        : `<button type="button" class="boton boton-chico" ${datos}>Calificar</button>`;
}

function formularioResena({ idVenta, idProducto, nombre }) {
    const existente = resenasDelPedido[`${idVenta}-${idProducto}`];

    return new Promise((resolver) => {
        const { elemento, cerrar } = abrirModal({
            titulo: existente ? "Editar reseña" : "Calificar compra",
            chico: true,
            contenido: `
                <form id="form-resena" novalidate>
                    <p class="u-mt-0">${esc(nombre)}</p>
                    <div class="campo"><label>¿Qué tal el producto?</label>${selectorEstrellas("estrellas-producto", existente ? existente.calificacion_producto : 0)}</div>
                    <div class="campo"><label>¿Qué tal el vendedor? <span class="ayuda u-en-linea">(atención, empaque y envío)</span></label>${selectorEstrellas("estrellas-vendedor", existente ? existente.calificacion_vendedor : 0)}</div>
                    <div class="campo">
                        <label for="comentario">Comentario <span class="ayuda u-en-linea">(opcional)</span></label>
                        <textarea class="control" id="comentario" maxlength="1000" rows="4" placeholder="Cuenta cómo llegó el producto y cómo fue la experiencia">${esc(existente ? existente.comentario || "" : "")}</textarea>
                    </div>
                    <div class="mensaje mensaje-error oculto" id="error-resena"></div>
                    <div class="grupo-botones u-al-final">
                        <button type="button" class="boton boton-secundario" data-cancelar>Volver</button>
                        <button type="submit" class="boton" id="enviar-resena">${existente ? "Guardar reseña" : "Publicar reseña"}</button>
                    </div>
                </form>`
        });

        const form = elemento.querySelector("#form-resena");
        const error = elemento.querySelector("#error-resena");
        let guardada = false;
        elemento.querySelector("[data-cancelar]").addEventListener("click", cerrar);

        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const producto = Number((form.querySelector("[name=estrellas-producto]:checked") || {}).value);
            const vendedor = Number((form.querySelector("[name=estrellas-vendedor]:checked") || {}).value);

            if (!producto || !vendedor) {
                error.textContent = "Elige de 1 a 5 estrellas para el producto y para el vendedor.";
                error.classList.remove("oculto");
                return;
            }

            const cuerpo = { calificacion_producto: producto, calificacion_vendedor: vendedor, comentario: form.comentario.value.trim() || null };

            await conBoton(elemento.querySelector("#enviar-resena"), async () => {
                try {
                    if (existente) await api("PUT", `/resenas/${existente.id_resena}`, { cuerpo });
                    else await api("POST", "/resenas/", { cuerpo: { ...cuerpo, id_venta: idVenta, id_producto: idProducto } });
                    guardada = true;
                    aviso(existente ? "Reseña actualizada." : "¡Gracias! Tu reseña ya es visible para otros compradores.", "exito");
                    cerrar();
                } catch (err) {
                    error.textContent = err.message;
                    error.classList.remove("oculto");
                }
            }, "Guardando...");
        });

        const observador = new MutationObserver(() => {
            if (!document.body.contains(elemento)) { observador.disconnect(); resolver(guardada); }
        });
        observador.observe(document.body, { childList: true });
    });
}

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

    const devoluciones = devolucionesDelPedido.filter((d) => d.id_venta === venta.id_venta);
    const enCurso = devoluciones.some((d) => ["SOLICITADA", "APROBADA", "ENVIADA"].includes(d.estado));
    const disponibles = productosDevolvibles(productos, devoluciones);
    if (venta.estado === "ENTREGADA") {
        if (enCurso) {
            acciones = `<span class="ayuda u-en-linea">Devolución en curso (ver abajo).</span>`;
        } else if (!disponibles.length) {
            acciones = `<span class="ayuda u-en-linea">No quedan unidades por devolver.</span>`;
        } else if (!(venta.dias_para_devolver > 0)) {
            acciones = `<span class="ayuda u-en-linea">El plazo de 15 días para devolver ya venció.</span>`;
        } else {
            acciones = `<button type="button" class="boton boton-secundario boton-chico" data-devolver="${venta.id_venta}">Solicitar devolución</button>
                        <span class="ayuda u-en-linea">${venta.dias_para_devolver} día${venta.dias_para_devolver === 1 ? "" : "s"} para devolver</span>`;
        }
    }

    return `
        <div class="tarjeta tarjeta-plana u-mb-12">
            <div class="u-fila-entre u-gap-10 u-envolver">
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
            <div class="tabla-envoltura u-mt-10">
                <table class="tabla">
                    <tbody>
                        ${productos.map((p) => `
                            <tr>
                                <td class="u-w-64"><div class="miniatura">${imagenProducto(p.imagen_principal, p.nombre)}</div></td>
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
                                ${venta.estado === "ENTREGADA" && p.cantidad_vigente > 0 ? `<td class="celda-resena">${botonResena(venta, p)}</td>` : ""}
                            </tr>`).join("")}
                    </tbody>
                </table>
            </div>
            ${devoluciones.map((d) => tarjetaDevolucion(d)).join("")}
        </div>`;
}

/* Unidades que aún se pueden devolver: vigentes menos las de devoluciones no rechazadas */
function productosDevolvibles(productos, devoluciones) {
    return productos.map((p) => {
        const devueltas = devoluciones.filter((d) => d.estado !== "RECHAZADA")
            .flatMap((d) => d.productos).filter((x) => x.id_producto === p.id_producto)
            .reduce((suma, x) => suma + x.cantidad, 0);
        return { ...p, disponible: p.cantidad_vigente - devueltas };
    }).filter((p) => p.disponible > 0);
}

function formularioDevolucion(venta, productos) {
    const { elemento, cerrar } = abrirModal({
        titulo: "Solicitar devolución",
        contenido: `
            <form id="form-devolucion" novalidate>
                <p class="u-mt-0">Elige qué quieres devolver. Si el vendedor aprueba, le envías el producto y, al recibirlo, se te reembolsa su valor.</p>
                <div class="lista-devolver">
                    ${productos.map((p) => `
                        <label class="opcion">
                            <input type="checkbox" name="producto" value="${p.id_producto}" data-precio="${p.precio_unitario}" checked>
                            <span>${esc(p.nombre)}<small>${precio(p.precio_unitario)} c/u · hasta ${p.disponible} und.</small></span>
                            <input class="control control-cantidad" type="number" min="1" max="${p.disponible}" value="${p.disponible}"
                                   data-cantidad="${p.id_producto}" aria-label="Unidades a devolver de ${esc(p.nombre)}">
                        </label>`).join("")}
                </div>
                <div class="campo">
                    <label for="motivo-dev">Motivo</label>
                    <select class="control" id="motivo-dev" name="motivo">
                        <option value="">Selecciona el motivo</option>
                        ${Object.entries(MOTIVOS_DEVOLUCION).map(([v, t]) => `<option value="${v}">${esc(t)}</option>`).join("")}
                    </select>
                </div>
                <div class="campo">
                    <label for="descripcion-dev">Describe el problema</label>
                    <textarea class="control" id="descripcion-dev" name="descripcion" maxlength="1000" rows="3"
                              placeholder="Ej.: la pantalla parpadea al encender; ocurre desde el primer día."></textarea>
                </div>
                <ul class="lista-datos"><li><span>Reembolso estimado</span><strong id="estimado-dev"></strong></li></ul>
                <div class="mensaje mensaje-error oculto" id="error-devolucion"></div>
                <div class="grupo-botones u-al-final">
                    <button type="button" class="boton boton-secundario" data-cancelar>Volver</button>
                    <button type="submit" class="boton" id="enviar-devolucion">Enviar solicitud</button>
                </div>
            </form>`
    });

    const form = elemento.querySelector("#form-devolucion");
    const error = elemento.querySelector("#error-devolucion");
    const elegidos = () => [...form.querySelectorAll("[name=producto]:checked")].map((c) => ({
        id_producto: Number(c.value),
        cantidad: Number(form.querySelector(`[data-cantidad="${c.value}"]`).value),
        precio: Number(c.dataset.precio),
        maximo: Number(form.querySelector(`[data-cantidad="${c.value}"]`).max)
    }));
    const actualizar = () => {
        elemento.querySelector("#estimado-dev").textContent = precio(elegidos().reduce((s, p) => s + p.precio * (p.cantidad || 0), 0));
    };
    form.addEventListener("input", actualizar);
    actualizar();
    elemento.querySelector("[data-cancelar]").addEventListener("click", cerrar);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const productosElegidos = elegidos();
        const fallas = [];
        if (!productosElegidos.length) fallas.push("Elige al menos un producto.");
        if (productosElegidos.some((p) => !Number.isInteger(p.cantidad) || p.cantidad < 1 || p.cantidad > p.maximo)) fallas.push("Revisa las unidades a devolver.");
        if (!form.motivo.value) fallas.push("Selecciona el motivo.");
        if (form.descripcion.value.trim().length < 10) fallas.push("Describe el problema (al menos 10 caracteres).");
        if (fallas.length) {
            error.innerHTML = fallas.map(esc).join("<br>");
            error.classList.remove("oculto");
            return;
        }

        await conBoton(elemento.querySelector("#enviar-devolucion"), async () => {
            try {
                await api("POST", "/devoluciones/", { cuerpo: {
                    id_venta: venta.id_venta, motivo: form.motivo.value, descripcion: form.descripcion.value.trim(),
                    productos: productosElegidos.map(({ id_producto, cantidad }) => ({ id_producto, cantidad }))
                } });
                cerrar();
                aviso("Solicitud de devolución enviada al vendedor.", "exito");
                alCambiarDevolucion();
            } catch (err) {
                error.textContent = err.message;
                error.classList.remove("oculto");
            }
        }, "Enviando...");
    });
}

async function abrirDetalle(idPedido) {
    const { elemento, cerrar } = abrirModal({
        titulo: `Pedido #${idPedido}`,
        contenido: `<div class="cargando">Cargando...</div>`
    });

    const cuerpo = elemento.querySelector(".modal-cuerpo");

    async function recargar() {
        try {
            const [pedido, resenas, devoluciones] = await Promise.all([
                api("GET", `/pedidos/${idPedido}`),
                api("GET", `/resenas/mias?id_pedido=${idPedido}`).catch(() => []),
                api("GET", `/devoluciones/?rol=COMPRADOR&id_pedido=${idPedido}`).catch(() => [])
            ]);
            devolucionesDelPedido = devoluciones;
            recargarDetalle = recargar;
            resenasDelPedido = Object.fromEntries(resenas.map((r) => [`${r.id_venta}-${r.id_producto}`, r]));
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
        <div class="u-fila-entre u-gap-10 u-envolver u-mb-14">
            <div>${etiquetaEstado(pedido.estado)} <span class="ayuda u-en-linea">· ${fecha(pedido.fecha, true)}</span></div>
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
            ${pedido.total_cancelado > 0 ? `<li><span>Estado del reembolso</span><span>${pago && ["REEMBOLSO_PARCIAL", "REEMBOLSADO"].includes(pago.estado) ? etiquetaEstado(pago.estado) : '<span class="estado estado-alerta">En proceso</span>'}</span></li>` : ""}
            <li><span>Total</span><span>${precio(pedido.total)}</span></li>
            ${pedido.total_cancelado > 0 ? `
                <li><span>Valor cancelado (se reembolsa)</span><span>− ${precio(pedido.total_cancelado)}</span></li>
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

        <div id="reembolsos-pedido"></div>

        <h3>Historial</h3>
        <button type="button" class="boton-texto" id="ver-historial">Ver historial de estados</button>
        <div id="historial"></div>`;

    cargarReembolsosPedido(pedido.id_pedido);

    const avisarCambio = () => cuerpo.closest(".modal").dispatchEvent(new Event("pedido-cambio"));

    // Solicitar devolución de una venta entregada
    cuerpo.querySelectorAll("[data-devolver]").forEach((b) =>
        b.addEventListener("click", () => {
            const venta = pedido.ventas.find((v) => v.id_venta === Number(b.dataset.devolver));
            const productos = pedido.productos.filter((p) => p.id_venta === venta.id_venta);
            formularioDevolucion(venta, productosDevolvibles(productos, devolucionesDelPedido.filter((d) => d.id_venta === venta.id_venta)));
        })
    );

    // Calificar productos entregados
    cuerpo.querySelectorAll("[data-resenar]").forEach((b) =>
        b.addEventListener("click", async () => {
            const guardada = await formularioResena({
                idVenta: Number(b.dataset.resenar), idProducto: Number(b.dataset.producto), nombre: b.dataset.nombre
            });
            if (guardada) avisarCambio();
        })
    );

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
                aviso(r.estado === "SOLICITADA" ? "Solicitud enviada al vendedor." : `Cancelación aplicada. Reembolso de ${precio(r.monto_reembolso)} en proceso.`, "exito");
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
                        : `Pedido cancelado. Reembolso de ${precio(r.monto_reembolsado)} en proceso; lo verás en «Mis reembolsos».`,
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
                <p class="u-mt-0">Marca los productos y las unidades que quieres cancelar. Solo aparecen los que aún no se han despachado.</p>
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
                                        <input type="number" class="control u-w-80" min="1" max="${p.cantidad_vigente}"
                                               value="${p.cantidad_vigente}" data-cantidad="${p.id_producto}" disabled>
                                    </td>
                                </tr>`).join("")}
                        </tbody>
                    </table>
                </div>
                <div class="campo u-mt-14">
                    <label for="motivo-parcial">Motivo</label>
                    <textarea class="control" id="motivo-parcial" maxlength="500" placeholder="Cuéntanos por qué cancelas"></textarea>
                </div>
                <div class="linea u-fila-entre u-negrita u-tinta">
                    <span>Reembolso estimado</span><span id="reembolso">${precio(0)}</span>
                </div>
                <div class="grupo-botones u-al-final u-mt-14">
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
