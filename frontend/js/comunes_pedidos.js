"use strict";

/* Funciones compartidas por "Mis compras" y "Mis ventas" */

const ESTADOS_SIN_DESPACHAR = ["PENDIENTE", "PREPARANDO"];

function pedirMotivo({ titulo, explicacion, textoBoton = "Confirmar", etiqueta = "Motivo", minimo = 5, opcional = false }) {
    return new Promise((resolver) => {
        const { elemento, cerrar } = abrirModal({
            titulo,
            chico: true,
            contenido: `
                <form id="form-motivo" novalidate>
                    ${explicacion ? `<p style="margin-top:0">${esc(explicacion)}</p>` : ""}
                    <div class="campo">
                        <label for="motivo">${esc(etiqueta)}${opcional ? ' <span class="ayuda" style="display:inline">(opcional)</span>' : ""}</label>
                        <textarea class="control" id="motivo" maxlength="500"></textarea>
                        <div class="error-campo oculto" id="error-motivo">Escribe al menos ${minimo} caracteres.</div>
                    </div>
                    <div class="grupo-botones" style="justify-content:flex-end">
                        <button type="button" class="boton boton-secundario" data-cancelar>Volver</button>
                        <button type="submit" class="boton">${esc(textoBoton)}</button>
                    </div>
                </form>`
        });

        let valor = null;
        const form = elemento.querySelector("#form-motivo");

        elemento.querySelector("[data-cancelar]").addEventListener("click", cerrar);

        form.addEventListener("submit", (e) => {
            e.preventDefault();
            const texto = form.motivo.value.trim();

            if (!opcional && texto.length < minimo) {
                elemento.querySelector("#error-motivo").classList.remove("oculto");
                return;
            }

            valor = texto;
            cerrar();
        });

        setTimeout(() => form.motivo.focus(), 50);

        const observador = new MutationObserver(() => {
            if (!document.body.contains(elemento)) {
                observador.disconnect();
                resolver(valor);
            }
        });
        observador.observe(document.body, { childList: true });
    });
}

async function verSeguimiento(idEnvio) {
    const { elemento } = abrirModal({
        titulo: "Seguimiento del envío",
        chico: true,
        contenido: `<div class="cargando">Cargando...</div>`
    });

    const cuerpo = elemento.querySelector(".modal-cuerpo");

    try {
        const s = await api("GET", `/envios/${idEnvio}`);

        cuerpo.innerHTML = `
            <ul class="lista-datos">
                <li><span>Estado</span><span>${etiquetaEstado(s.estado_envio)}</span></li>
                <li><span>Transportadora</span><span>${esc(s.transportadora)}</span></li>
                <li><span>Guía</span><span>${esc(s.numero_guia)}</span></li>
                <li><span>Despachado</span><span>${fecha(s.fecha_despacho, true)}</span></li>
                <li><span>Entregado</span><span>${fecha(s.fecha_entrega, true)}</span></li>
                <li><span>Destino</span><span>${esc(s.entrega.ciudad)}, ${esc(s.entrega.departamento)}</span></li>
            </ul>
            <h3>Historial</h3>
            <ol class="linea-tiempo">
                ${s.historial.map((h) => `
                    <li>
                        <strong>${esc(textoEstado(h.estado))}</strong>
                        <div class="fecha">${fecha(h.fecha, true)}</div>
                        ${h.observacion ? `<div>${esc(h.observacion)}</div>` : ""}
                    </li>`).join("")}
            </ol>`;
    } catch (e) {
        cuerpo.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
    }
}

function tablaCancelaciones(cancelaciones) {
    if (!cancelaciones || !cancelaciones.length) return "";

    return `
        <h3>Cancelaciones</h3>
        <div class="tabla-envoltura">
            <table class="tabla">
                <thead><tr><th>#</th><th>Tipo</th><th>Estado</th><th>Motivo</th><th class="numero">Reembolso</th><th>Fecha</th></tr></thead>
                <tbody>
                    ${cancelaciones.map((c) => `
                        <tr>
                            <td>${c.id_cancelacion}</td>
                            <td>${c.tipo === "TOTAL" ? "Total" : "Parcial"}</td>
                            <td>${etiquetaEstado(c.estado)}</td>
                            <td>${esc(c.motivo)}</td>
                            <td class="numero">${precio(c.monto_reembolso)}</td>
                            <td>${fecha(c.fecha_solicitud)}</td>
                        </tr>`).join("")}
                </tbody>
            </table>
        </div>`;
}
