"use strict";

/* Formulario de dirección reutilizable (compra y perfil) */

const DEPARTAMENTOS = [
    "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bogotá D.C.", "Bolívar",
    "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó",
    "Córdoba", "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira",
    "Magdalena", "Meta", "Nariño", "Norte de Santander", "Putumayo", "Quindío",
    "Risaralda", "San Andrés y Providencia", "Santander", "Sucre", "Tolima",
    "Valle del Cauca", "Vaupés", "Vichada"
];

function formularioDireccion(d = {}) {
    const opciones = DEPARTAMENTOS.map((dep) =>
        `<option value="${esc(dep)}" ${d.departamento === dep ? "selected" : ""}>${esc(dep)}</option>`
    ).join("");

    // Conserva un departamento guardado que no esté en la lista
    const extra = d.departamento && !DEPARTAMENTOS.includes(d.departamento)
        ? `<option value="${esc(d.departamento)}" selected>${esc(d.departamento)}</option>`
        : "";

    return `
        <div class="campo">
            <label>Dirección</label>
            <input class="control" name="direccion" maxlength="200" placeholder="Ej: Calle 10 # 20-30, apto 501"
                   value="${esc(d.direccion || "")}" required>
        </div>
        <div class="fila fila-2">
            <div class="campo">
                <label>Departamento</label>
                <select class="control" name="departamento" required>
                    <option value="">Selecciona</option>${extra}${opciones}
                </select>
            </div>
            <div class="campo">
                <label>Ciudad</label>
                <input class="control" name="ciudad" maxlength="100" placeholder="Ciudad o municipio"
                       value="${esc(d.ciudad || "")}" required>
            </div>
        </div>
        <div class="campo">
            <label>Código postal <span class="ayuda" style="display:inline">(opcional)</span></label>
            <input class="control" name="codigo_postal" maxlength="20" value="${esc(d.codigo_postal || "")}">
        </div>`;
}

function leerDireccion(form) {
    return {
        direccion: form.direccion.value.trim(),
        ciudad: form.ciudad.value.trim(),
        departamento: form.departamento.value,
        codigo_postal: form.codigo_postal.value.trim() || null
    };
}

function validarDireccion(datos) {
    const errores = [];
    if (datos.direccion.length < 5) errores.push("Escribe la dirección completa (mínimo 5 caracteres).");
    if (!datos.departamento) errores.push("Selecciona el departamento.");
    if (datos.ciudad.length < 2) errores.push("Escribe la ciudad.");
    return errores;
}

function textoDireccion(d) {
    return `${d.direccion}, ${d.ciudad}, ${d.departamento}${d.codigo_postal ? " · CP " + d.codigo_postal : ""}`;
}

/* Abre una ventana para crear o editar una dirección. Devuelve la dirección guardada o null. */
function editarDireccionModal(direccion = null) {
    return new Promise((resolver) => {
        const { elemento, cerrar } = abrirModal({
            titulo: direccion ? "Editar dirección" : "Nueva dirección",
            chico: true,
            contenido: `
                <form id="form-direccion" novalidate>
                    <div id="msg-direccion"></div>
                    ${formularioDireccion(direccion || {})}
                    <div class="grupo-botones" style="justify-content:flex-end">
                        <button type="button" class="boton boton-secundario" id="cancelar-direccion">Cancelar</button>
                        <button type="submit" class="boton">Guardar dirección</button>
                    </div>
                </form>`
        });

        let guardada = null;

        const form = elemento.querySelector("#form-direccion");
        elemento.querySelector("#cancelar-direccion").addEventListener("click", cerrar);

        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const datos = leerDireccion(form);
            const errores = validarDireccion(datos);
            const caja = elemento.querySelector("#msg-direccion");

            if (errores.length) {
                mostrarMensaje(caja, "Revisa los datos:", "error", errores);
                return;
            }

            await conBoton(form.querySelector("[type=submit]"), async () => {
                try {
                    guardada = direccion
                        ? await api("PUT", `/direcciones/${direccion.id_direccion}`, { cuerpo: datos })
                        : await api("POST", "/direcciones/", { cuerpo: datos });
                    cerrar();
                } catch (err) {
                    mostrarMensaje(caja, err.message, "error");
                }
            }, "Guardando...");
        });

        const observador = new MutationObserver(() => {
            if (!document.body.contains(elemento)) {
                observador.disconnect();
                resolver(guardada);
            }
        });
        observador.observe(document.body, { childList: true });
    });
}
