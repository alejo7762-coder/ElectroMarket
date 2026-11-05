"use strict";

function cambiarPestana(nombre) {
    document.querySelectorAll("[data-pestana]").forEach((b) =>
        b.classList.toggle("activa", b.dataset.pestana === nombre)
    );

    ["datos", "seguridad", "direcciones"].forEach((p) =>
        document.getElementById(`pestana-${p}`).classList.toggle("oculto", p !== nombre)
    );

    if (nombre === "direcciones") cargarDirecciones();
}

/* Datos personales */

async function cargarPerfil() {
    const form = document.getElementById("form-datos");

    try {
        const u = await api("GET", "/usuarios/me");

        form.nombre.value = u.nombre || "";
        form.apellido.value = u.apellido || "";
        form.telefono.value = u.telefono || "";
        form.fecha_nacimiento.value = u.fecha_nacimiento || "";
        form.genero.value = u.genero || "";
        document.getElementById("correo").value = u.correo;
        document.getElementById("miembro-desde").textContent = `Miembro desde ${fecha(u.fecha_registro)}.`;
    } catch (e) {
        mostrarMensaje(document.getElementById("msg-datos"), e.message, "error");
    }
}

async function guardarPerfil(e) {
    e.preventDefault();

    const form = e.target;
    const caja = document.getElementById("msg-datos");
    const datos = {
        nombre: form.nombre.value.trim(),
        apellido: form.apellido.value.trim(),
        telefono: form.telefono.value.trim() || null,
        fecha_nacimiento: form.fecha_nacimiento.value || null,
        genero: form.genero.value || null
    };

    const errores = [];
    if (datos.nombre.length < 2) errores.push("Escribe tu nombre.");
    if (datos.apellido.length < 2) errores.push("Escribe tu apellido.");
    if (datos.telefono && !/^\+?[0-9 ]{7,20}$/.test(datos.telefono)) errores.push("El celular solo puede tener números (mínimo 7).");

    if (errores.length) {
        mostrarMensaje(caja, "Revisa los datos:", "error", errores);
        return;
    }

    await conBoton(form.querySelector("[type=submit]"), async () => {
        try {
            const r = await api("PUT", "/usuarios/me", { cuerpo: datos });
            Sesion.actualizarUsuario({ nombre: r.usuario.nombre, apellido: r.usuario.apellido });
            montarEncabezado();
            mostrarMensaje(caja, "Tus datos se guardaron correctamente.", "exito");
        } catch (err) {
            mostrarMensaje(caja, err.message, "error");
        }
    }, "Guardando...");
}

/* Contraseña */

async function cambiarContrasena(e) {
    e.preventDefault();

    const form = e.target;
    const caja = document.getElementById("msg-contrasena");
    const actual = form.actual.value;
    const nueva = form.nueva.value;

    if (!actual) return mostrarMensaje(caja, "Escribe tu contraseña actual.", "error");
    if (nueva.length < 8) return mostrarMensaje(caja, "La nueva contraseña debe tener al menos 8 caracteres.", "error");
    if (nueva !== form.repetir.value) return mostrarMensaje(caja, "Las contraseñas nuevas no coinciden.", "error");

    await conBoton(form.querySelector("[type=submit]"), async () => {
        try {
            await api("PUT", "/usuarios/me/contrasena", {
                cuerpo: { contrasena_actual: actual, contrasena_nueva: nueva }
            });
            form.reset();
            mostrarMensaje(caja, "Tu contraseña se cambió correctamente.", "exito");
        } catch (err) {
            mostrarMensaje(caja, err.message, "error");
        }
    }, "Guardando...");
}

/* Direcciones */

let direcciones = [];

async function cargarDirecciones() {
    const lista = document.getElementById("lista-direcciones");

    try {
        direcciones = await api("GET", "/direcciones/");

        if (!direcciones.length) {
            lista.innerHTML = `<div class="vacio" style="padding:24px">Aún no tienes direcciones registradas.</div>`;
            return;
        }

        lista.innerHTML = direcciones.map((d) => `
            <div class="opcion" style="cursor:default;justify-content:space-between;align-items:center">
                <span>${esc(d.direccion)}<small>${esc(d.ciudad)}, ${esc(d.departamento)}${d.codigo_postal ? " · CP " + esc(d.codigo_postal) : ""}</small></span>
                <span class="grupo-botones">
                    <button type="button" class="boton boton-secundario boton-chico" data-editar="${d.id_direccion}">Editar</button>
                    <button type="button" class="boton boton-secundario boton-chico" data-eliminar="${d.id_direccion}">Eliminar</button>
                </span>
            </div>`).join("");
    } catch (e) {
        lista.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
    }
}

async function accionesDirecciones(e) {
    const editar = e.target.closest("[data-editar]");
    const eliminar = e.target.closest("[data-eliminar]");

    if (editar) {
        const d = direcciones.find((x) => x.id_direccion === Number(editar.dataset.editar));
        if (await editarDireccionModal(d)) {
            aviso("Dirección actualizada.", "exito");
            cargarDirecciones();
        }
    }

    if (eliminar) {
        const ok = await confirmar("¿Eliminar esta dirección?", { titulo: "Eliminar dirección", textoBoton: "Eliminar", peligro: true });
        if (!ok) return;

        try {
            await api("DELETE", `/direcciones/${eliminar.dataset.eliminar}`);
            aviso("Dirección eliminada.", "exito");
        } catch (err) {
            aviso(err.message, "error");
        }
        cargarDirecciones();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    if (!requerirSesion()) return;

    document.querySelectorAll("[data-pestana]").forEach((b) =>
        b.addEventListener("click", () => cambiarPestana(b.dataset.pestana))
    );

    document.getElementById("form-datos").addEventListener("submit", guardarPerfil);
    document.getElementById("form-contrasena").addEventListener("submit", cambiarContrasena);
    document.getElementById("lista-direcciones").addEventListener("click", accionesDirecciones);
    document.getElementById("nueva-direccion").addEventListener("click", async () => {
        if (await editarDireccionModal()) {
            aviso("Dirección agregada.", "exito");
            cargarDirecciones();
        }
    });

    cargarPerfil();

    if (window.location.hash === "#direcciones") cambiarPestana("direcciones");
});
