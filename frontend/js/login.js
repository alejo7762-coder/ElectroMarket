"use strict";

async function ingresar(evento) {
    evento.preventDefault();

    const form = evento.target;
    const caja = document.getElementById("mensaje");
    const correo = form.correo.value.trim().toLowerCase();
    const contrasena = form.contrasena.value;

    if (!correo || !contrasena) {
        mostrarMensaje(caja, "Escribe tu correo y tu contraseña.", "error");
        return;
    }

    await conBoton(document.getElementById("boton-ingreso"), async () => {
        try {
            const sesion = await api("POST", "/usuarios/login", {
                autenticado: false,
                cuerpo: { correo, contrasena }
            });

            Sesion.iniciar(sesion.access_token, sesion.usuario);
            window.location.href = destinoSeguro(parametro("volver"));

        } catch (e) {
            mostrarMensaje(caja, e.message, "error");
        }
    }, "Ingresando...");
}

document.addEventListener("DOMContentLoaded", () => {
    const volver = parametro("volver");
    const mensaje = parametro("mensaje");

    if (mensaje) {
        mostrarMensaje(document.getElementById("mensaje"), mensaje, "info");
    }

    if (volver) {
        document.getElementById("enlace-registro").href =
            `registro.html?volver=${encodeURIComponent(volver)}`;
    }

    document.getElementById("formulario-ingreso").addEventListener("submit", ingresar);
});
