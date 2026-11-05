"use strict";

let carrito = null;
let direcciones = [];

function pintarDirecciones(seleccionada) {
    const lista = document.getElementById("lista-direcciones");

    if (!direcciones.length) {
        lista.innerHTML = `<div class="mensaje mensaje-info">Aún no tienes direcciones. Agrega una para continuar.</div>`;
        return;
    }

    const elegida = seleccionada || direcciones[direcciones.length - 1].id_direccion;

    lista.innerHTML = direcciones.map((d) => `
        <label class="opcion">
            <input type="radio" name="direccion" value="${d.id_direccion}" ${d.id_direccion === elegida ? "checked" : ""}>
            <span>${esc(d.direccion)}<small>${esc(d.ciudad)}, ${esc(d.departamento)}${d.codigo_postal ? " · CP " + esc(d.codigo_postal) : ""}</small></span>
        </label>`).join("");
}

function pintarPagina() {
    const items = carrito.productos;
    const unidades = items.reduce((s, p) => s + p.cantidad, 0);

    document.getElementById("contenido").innerHTML = `
        <div class="distribucion-compra">
            <div>
                <section class="tarjeta">
                    <h2>1. Dirección de entrega</h2>
                    <div id="lista-direcciones"></div>
                    <button type="button" class="boton boton-secundario boton-chico" id="nueva-direccion">+ Agregar dirección</button>
                </section>

                <section class="tarjeta">
                    <h2>2. Método de pago</h2>
                    <div class="mensaje mensaje-info">Los pagos son simulados: no se realiza ningún cobro real.</div>

                    <label class="opcion">
                        <input type="radio" name="metodo" value="SIMULADO" checked>
                        <span>Pago simulado<small>Se aprueba automáticamente.</small></span>
                    </label>
                    <label class="opcion">
                        <input type="radio" name="metodo" value="TRANSFERENCIA_SIMULADA">
                        <span>Transferencia bancaria (simulada)<small>Se aprueba automáticamente.</small></span>
                    </label>
                    <label class="opcion">
                        <input type="radio" name="metodo" value="TARJETA_SIMULADA">
                        <span>Tarjeta de crédito o débito (simulada)<small>Las tarjetas terminadas en 0000 se rechazan, para probar pagos fallidos.</small></span>
                    </label>

                    <div class="campo oculto" id="campo-tarjeta" style="margin-top:12px">
                        <label for="tarjeta">Número de tarjeta</label>
                        <input class="control" id="tarjeta" inputmode="numeric" autocomplete="off"
                               placeholder="0000 0000 0000 0000" maxlength="19">
                        <div class="ayuda">16 dígitos. El número no se guarda.</div>
                    </div>
                </section>
            </div>

            <aside class="tarjeta resumen">
                <h2>Tu pedido</h2>
                ${items.map((p) => `
                    <div class="linea" style="gap:12px"><span>${esc(p.nombre)} <span class="ayuda" style="display:inline">× ${p.cantidad}</span></span><span style="white-space:nowrap">${precio(p.subtotal)}</span></div>`).join("")}
                <div class="linea"><span>Envío</span><span>Gratis</span></div>
                <div class="linea total"><span>Total (${unidades} und.)</span><span>${precio(carrito.total)}</span></div>
                <div id="mensaje-compra" style="margin-top:14px"></div>
                <button type="button" class="boton boton-bloque boton-grande" id="confirmar" style="margin-top:6px">Pagar ${precio(carrito.total)}</button>
                <a class="boton boton-secundario boton-bloque" href="carrito.html" style="margin-top:8px">Volver al carrito</a>
            </aside>
        </div>`;

    pintarDirecciones();

    document.getElementById("nueva-direccion").addEventListener("click", async () => {
        const nueva = await editarDireccionModal();
        if (nueva) {
            direcciones = await api("GET", "/direcciones/");
            pintarDirecciones(nueva.id_direccion);
            mostrarMensaje(document.getElementById("mensaje-compra"), "");
            aviso("Dirección agregada.", "exito");
        }
    });

    document.querySelectorAll("input[name=metodo]").forEach((r) =>
        r.addEventListener("change", () => {
            document.getElementById("campo-tarjeta").classList.toggle(
                "oculto", document.querySelector("input[name=metodo]:checked").value !== "TARJETA_SIMULADA"
            );
        })
    );

    const tarjeta = document.getElementById("tarjeta");
    tarjeta.addEventListener("input", () => {
        const digitos = tarjeta.value.replace(/\D/g, "").slice(0, 16);
        tarjeta.value = digitos.replace(/(\d{4})(?=\d)/g, "$1 ");
    });

    document.getElementById("confirmar").addEventListener("click", comprar);
}

function pintarResultadoExitoso(r) {
    actualizarContadorCarrito(0);

    document.getElementById("contenido").innerHTML = `
        <section class="tarjeta" style="max-width:640px;margin:0 auto;text-align:center">
            <div style="font-size:46px;color:var(--exito)">✓</div>
            <h2 style="font-size:22px">¡Compra realizada!</h2>
            <p>Tu pedido <strong>#${r.id_pedido}</strong> fue pagado y confirmado.</p>
            <ul class="lista-datos" style="text-align:left;margin:20px 0">
                <li><span>Total pagado</span><span>${precio(r.total)}</span></li>
                <li><span>Método</span><span>${esc(METODOS_PAGO[r.pago.metodo] || r.pago.metodo)}</span></li>
                <li><span>Referencia</span><span>${esc(r.pago.referencia)}</span></li>
                <li><span>Vendedores</span><span>${r.ventas.length}</span></li>
            </ul>
            <p class="ayuda">Cada vendedor preparará su parte del pedido. Puedes seguir el envío desde “Mis compras”.</p>
            <div class="grupo-botones" style="justify-content:center;margin-top:16px">
                <a class="boton" href="pedidos.html?pedido=${r.id_pedido}">Ver mi pedido</a>
                <a class="boton boton-secundario" href="index.html">Seguir comprando</a>
            </div>
        </section>`;
}

async function comprar() {
    const caja = document.getElementById("mensaje-compra");
    const direccion = document.querySelector("input[name=direccion]:checked");
    const metodo = document.querySelector("input[name=metodo]:checked").value;
    const numero = document.getElementById("tarjeta").value.replace(/\D/g, "");

    if (!direccion) {
        mostrarMensaje(caja, "Agrega o selecciona una dirección de entrega.", "error");
        return;
    }

    if (metodo === "TARJETA_SIMULADA" && numero.length !== 16) {
        mostrarMensaje(caja, "El número de tarjeta debe tener 16 dígitos.", "error");
        return;
    }

    mostrarMensaje(caja, "");

    await conBoton(document.getElementById("confirmar"), async () => {
        try {
            const r = await api("POST", "/pedidos/comprar", {
                cuerpo: {
                    id_direccion: Number(direccion.value),
                    metodo_pago: metodo,
                    numero_tarjeta: metodo === "TARJETA_SIMULADA" ? numero : null
                }
            });
            pintarResultadoExitoso(r);

        } catch (e) {
            if (e.status === 402) {
                mostrarMensaje(caja, "El pago fue rechazado. Tu carrito se conservó: prueba con otro método o con otra tarjeta.", "error");
            } else if (e.status === 409 && e.datos && e.datos.detail && e.datos.detail.productos) {
                mostrarMensaje(
                    caja,
                    "Algunos productos ya no se pueden comprar:",
                    "error",
                    e.datos.detail.productos.map((p) => `${p.nombre}: ${p.motivo}`)
                );
            } else {
                mostrarMensaje(caja, e.message, "error");
            }
        }
    }, "Procesando pago...");
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!requerirSesion()) return;

    try {
        [carrito, direcciones] = await Promise.all([
            api("GET", "/carrito/"),
            api("GET", "/direcciones/")
        ]);

        if (!carrito.productos || !carrito.productos.length) {
            document.getElementById("contenido").innerHTML = `
                <div class="tarjeta vacio">${ICONOS.carrito}<p>Tu carrito está vacío.</p>
                <a class="boton" href="index.html">Ir a la tienda</a></div>`;
            return;
        }

        pintarPagina();
    } catch (e) {
        document.getElementById("contenido").innerHTML = `<div class="tarjeta vacio">${esc(e.message)}</div>`;
    }
});
