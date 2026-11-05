"use strict";

const MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
];

function llenarFechas() {
    const form = document.getElementById("formulario-registro");
    const anioActual = new Date().getFullYear();

    for (let d = 1; d <= 31; d++) {
        form.dia.add(new Option(String(d), String(d)));
    }

    MESES.forEach((m, i) => form.mes.add(new Option(m, String(i + 1))));

    for (let a = anioActual - 18; a >= anioActual - 100; a--) {
        form.anio.add(new Option(String(a), String(a)));
    }
}

function fechaSeleccionada(form) {
    const d = Number(form.dia.value);
    const m = Number(form.mes.value);
    const a = Number(form.anio.value);

    if (!d || !m || !a) return { error: "Selecciona tu fecha de nacimiento completa." };

    const fechaObj = new Date(a, m - 1, d);
    if (fechaObj.getMonth() !== m - 1) return { error: "La fecha de nacimiento no existe." };

    const texto = `${a}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    return { valor: texto };
}

function validar(form) {
    const errores = [];

    if (form.nombre.value.trim().length < 2) errores.push("Escribe tu nombre.");
    if (form.apellido.value.trim().length < 2) errores.push("Escribe tu apellido.");

    const f = fechaSeleccionada(form);
    if (f.error) errores.push(f.error);

    if (!form.genero.value) errores.push("Selecciona tu género.");

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.correo.value.trim())) {
        errores.push("Escribe un correo electrónico válido.");
    }

    const tel = form.telefono.value.trim();
    if (tel && !/^\+?[0-9 ]{7,20}$/.test(tel)) {
        errores.push("El celular solo puede tener números (mínimo 7).");
    }

    if (form.contrasena.value.length < 8) {
        errores.push("La contraseña debe tener al menos 8 caracteres.");
    }

    return { errores, fecha: f.valor };
}

async function registrar(evento) {
    evento.preventDefault();

    const form = evento.target;
    const caja = document.getElementById("mensaje");
    const { errores, fecha } = validar(form);

    if (errores.length) {
        mostrarMensaje(caja, "Revisa los datos:", "error", errores);
        caja.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }

    mostrarMensaje(caja, "");

    const correo = form.correo.value.trim().toLowerCase();
    const contrasena = form.contrasena.value;

    await conBoton(document.getElementById("boton-registro"), async () => {
        try {
            await api("POST", "/usuarios/registro", {
                autenticado: false,
                cuerpo: {
                    nombre: form.nombre.value.trim(),
                    apellido: form.apellido.value.trim(),
                    correo,
                    contrasena,
                    telefono: form.telefono.value.trim() || null,
                    fecha_nacimiento: fecha,
                    genero: form.genero.value
                }
            });

            // Ingresar automáticamente
            const sesion = await api("POST", "/usuarios/login", {
                autenticado: false,
                cuerpo: { correo, contrasena }
            });

            Sesion.iniciar(sesion.access_token, sesion.usuario);
            window.location.href = destinoSeguro(parametro("volver"));

        } catch (e) {
            mostrarMensaje(caja, e.message, "error");
        }
    }, "Creando cuenta...");
}

document.addEventListener("DOMContentLoaded", () => {
    if (Sesion.activa()) {
        window.location.href = "index.html";
        return;
    }

    llenarFechas();
    document.getElementById("formulario-registro").addEventListener("submit", registrar);
});
