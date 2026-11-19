"use strict";

/* Devoluciones después de la entrega: compartido por "Mis compras" y "Mis ventas".
   Cada página define alCambiarDevolucion() para recargar lo que muestra. */

const MOTIVOS_DEVOLUCION = {
    DEFECTUOSO: "El producto presenta fallas",
    NO_COINCIDE: "No coincide con la descripción",
    LLEGO_DANADO: "Llegó dañado",
    EQUIVOCADO: "Recibí un producto equivocado",
    ARREPENTIMIENTO: "Ya no lo quiero"
};

const PASOS_DEVOLUCION = [
    ["SOLICITADA", "Solicitada", "fecha_solicitud"],
    ["APROBADA", "Aprobada", "fecha_respuesta"],
    ["ENVIADA", "Enviada por el comprador", "fecha_envio"],
    ["RECIBIDA", "Recibida por el vendedor", "fecha_recepcion"]
];

function pasosDevolucion(d) {
    if (d.estado === "RECHAZADA") {
        return `<div class="mensaje mensaje-error u-mt-8">${icono("cerrar")} Rechazada el ${fecha(d.fecha_respuesta)}${d.observacion_vendedor ? `: ${esc(d.observacion_vendedor)}` : ""}</div>`;
    }
    const actual = PASOS_DEVOLUCION.findIndex(([estado]) => estado === d.estado);
    return `<ol class="linea-reembolso pasos-devolucion">${PASOS_DEVOLUCION.map(([, texto, campo], i) => `
        <li class="${i <= actual ? "hecho" : i === actual + 1 ? "actual" : ""}">
            <strong>${icono(i <= actual ? "check" : "reloj")}${texto}</strong>
            <span>${i <= actual && d[campo] ? fecha(d[campo], true) : "Pendiente"}</span>
        </li>`).join("")}</ol>`;
}

function accionesDevolucion(d) {
    const id = d.id_devolucion;
    if (d.rol === "COMPRADOR" && d.estado === "APROBADA") {
        return `<button type="button" class="boton boton-chico" data-dev-accion="enviar" data-dev="${id}">Registrar envío</button>`;
    }
    if (d.rol === "VENDEDOR" && d.estado === "SOLICITADA") {
        return `<button type="button" class="boton boton-chico" data-dev-accion="aprobar" data-dev="${id}">Aprobar devolución</button>
                <button type="button" class="boton boton-secundario boton-chico" data-dev-accion="rechazar" data-dev="${id}">Rechazar devolución</button>`;
    }
    if (d.rol === "VENDEDOR" && d.estado === "ENVIADA") {
        return `<button type="button" class="boton boton-chico" data-dev-accion="recibir" data-dev="${id}" data-monto="${d.monto_reembolso}">Confirmar recepción</button>`;
    }
    return "";
}

function tarjetaDevolucion(d, { mostrarPedido = false } = {}) {
    const ayuda = {
        SOLICITADA: d.rol === "COMPRADOR" ? "Esperando la respuesta del vendedor." : "Revisa la solicitud y apruébala o recházala.",
        APROBADA: d.rol === "COMPRADOR" ? "Envía el producto al vendedor y registra la guía." : "Esperando que el comprador envíe el producto.",
        ENVIADA: d.rol === "VENDEDOR" ? "Cuando recibas el producto, confirma la recepción para reembolsar al comprador." : "El vendedor confirmará la recepción y se generará tu reembolso.",
        RECIBIDA: `Reembolso de ${precio(d.monto_reembolso)} ${d.estado_reembolso === "PROCESADO" ? `procesado (${esc(d.referencia_reembolso || "")})` : "en proceso"}.`
    }[d.estado] || "";

    return `
        <article class="tarjeta-devolucion estado-dev-${d.estado.toLowerCase()}">
            <div class="u-fila-entre u-gap-10 u-envolver">
                <div>
                    <strong>${icono("reembolso")} Devolución #${d.id_devolucion}</strong> ${etiquetaEstado(d.estado)}
                    ${mostrarPedido ? `<span class="ayuda u-en-linea"> · Pedido #${d.id_pedido} · ${esc(d.rol === "VENDEDOR" ? d.comprador : d.vendedor)}</span>` : ""}
                    <div class="ayuda u-m-0">${esc(d.motivo_texto)} · ${d.productos.map((p) => `${esc(p.nombre)} × ${p.cantidad}`).join(", ")}</div>
                </div>
                <strong class="u-tinta">${precio(d.monto_reembolso)}</strong>
            </div>
            <p class="u-pre-linea u-mt-8">«${esc(d.descripcion)}»</p>
            ${d.numero_guia ? `<div class="ayuda u-m-0">${icono("camion")} ${esc(d.transportadora)} · Guía ${esc(d.numero_guia)}</div>` : ""}
            ${d.estado === "RECIBIDA" ? `<div class="ayuda u-m-0">${d.reintegrado_inventario ? "Las unidades volvieron al inventario." : "Las unidades no se reintegraron al inventario."}</div>` : ""}
            ${pasosDevolucion(d)}
            <div class="u-fila-entre u-gap-10 u-envolver u-mt-10">
                <small class="ayuda u-m-0">${ayuda}</small>
                <div class="grupo-botones">${accionesDevolucion(d)}</div>
            </div>
        </article>`;
}

/* --------------------------------------------------------------- acciones */

/* Modal con un formulario: construir(form) devuelve el cuerpo o un texto de error */
function accionDevolucion({ titulo, explicacion, campos, textoBoton, ruta, construir, mensaje }) {
    const { elemento, cerrar } = abrirModal({
        titulo, chico: true,
        contenido: `
            <form id="form-dev" novalidate>
                ${explicacion ? `<p class="u-mt-0">${explicacion}</p>` : ""}
                ${campos}
                <div class="mensaje mensaje-error oculto" id="error-dev"></div>
                <div class="grupo-botones u-al-final">
                    <button type="button" class="boton boton-secundario" data-cancelar>Volver</button>
                    <button type="submit" class="boton" id="enviar-dev">${esc(textoBoton)}</button>
                </div>
            </form>`
    });
    const form = elemento.querySelector("#form-dev");
    const error = elemento.querySelector("#error-dev");
    elemento.querySelector("[data-cancelar]").addEventListener("click", cerrar);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const cuerpo = construir(form);
        if (typeof cuerpo === "string") {
            error.textContent = cuerpo;
            error.classList.remove("oculto");
            return;
        }
        await conBoton(elemento.querySelector("#enviar-dev"), async () => {
            try {
                await api("POST", ruta, { cuerpo });
                cerrar();
                aviso(mensaje, "exito");
                if (typeof alCambiarDevolucion === "function") alCambiarDevolucion();
            } catch (err) {
                error.textContent = err.message;
                error.classList.remove("oculto");
            }
        }, "Guardando...");
    });
}

document.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-dev-accion]");
    if (!boton) return;
    const id = boton.dataset.dev;
    const accion = boton.dataset.devAccion;

    if (accion === "aprobar") {
        accionDevolucion({
            titulo: "Aprobar devolución", textoBoton: "Aprobar devolución",
            explicacion: "El comprador te enviará el producto. Puedes dejarle instrucciones (dirección, transportadora…).",
            campos: `<div class="campo"><label for="observacion">Instrucciones <span class="ayuda u-en-linea">(opcional)</span></label>
                     <textarea class="control" id="observacion" name="observacion" maxlength="500"></textarea></div>`,
            ruta: `/devoluciones/${id}/aprobar`, mensaje: "Devolución aprobada.",
            construir: (f) => ({ observacion: f.observacion.value.trim() || null })
        });
    } else if (accion === "rechazar") {
        accionDevolucion({
            titulo: "Rechazar devolución", textoBoton: "Rechazar devolución",
            explicacion: "Explica al comprador por qué no aceptas la devolución.",
            campos: `<div class="campo"><label for="observacion">Motivo del rechazo</label>
                     <textarea class="control" id="observacion" name="observacion" maxlength="500"></textarea></div>`,
            ruta: `/devoluciones/${id}/rechazar`, mensaje: "Devolución rechazada.",
            construir: (f) => f.observacion.value.trim().length < 5 ? "Escribe el motivo (al menos 5 caracteres)." : { observacion: f.observacion.value.trim() }
        });
    } else if (accion === "enviar") {
        accionDevolucion({
            titulo: "Registrar envío de la devolución", textoBoton: "Registrar envío",
            explicacion: "Indica con qué transportadora enviaste el producto y el número de guía.",
            campos: `<div class="campo"><label for="transportadora">Transportadora</label>
                     <input class="control" id="transportadora" name="transportadora" maxlength="100" placeholder="Ej: Servientrega"></div>
                     <div class="campo"><label for="numero_guia">Número de guía</label>
                     <input class="control" id="numero_guia" name="numero_guia" maxlength="100"></div>`,
            ruta: `/devoluciones/${id}/enviar`, mensaje: "Envío registrado. El vendedor confirmará la recepción.",
            construir: (f) => f.transportadora.value.trim().length < 2 || f.numero_guia.value.trim().length < 3
                ? "Escribe la transportadora y el número de guía."
                : { transportadora: f.transportadora.value.trim(), numero_guia: f.numero_guia.value.trim() }
        });
    } else if (accion === "recibir") {
        accionDevolucion({
            titulo: "Confirmar recepción", textoBoton: "Confirmar y reembolsar",
            explicacion: `Se reembolsarán <strong>${precio(Number(boton.dataset.monto))}</strong> al comprador.`,
            campos: `<label class="opcion"><input type="checkbox" name="reintegrar" checked>
                     <span>Devolver las unidades al inventario<small>Desmárcalo si el producto no se puede volver a vender (por ejemplo, si llegó dañado).</small></span></label>`,
            ruta: `/devoluciones/${id}/recibir`, mensaje: "Recepción confirmada: reembolso registrado.",
            construir: (f) => ({ reintegrar_inventario: f.reintegrar.checked })
        });
    }
});
