"use strict";

function problemaDe(item) {
    if (item.estado_producto !== "PUBLICADO") return "Este producto ya no está disponible.";
    if (item.stock_disponible < item.cantidad) {
        return `Solo quedan ${item.stock_disponible} unidad${item.stock_disponible === 1 ? "" : "es"}.`;
    }
    return null;
}

function pintar(carrito) {
    const contenido = document.getElementById("contenido");
    const items = carrito.productos || [];

    actualizarContadorCarrito(items.reduce((s, p) => s + p.cantidad, 0));

    if (!items.length) {
        contenido.innerHTML = `
            <div class="tarjeta vacio">
                ${ICONOS.carrito}
                <p>Tu carrito está vacío.</p>
                <a class="boton" href="index.html">Ir a la tienda</a>
            </div>`;
        return;
    }

    const conProblemas = items.filter(problemaDe);
    const unidades = items.reduce((s, p) => s + p.cantidad, 0);

    contenido.innerHTML = `
        <div class="distribucion-compra">
            <section class="tarjeta">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h2 style="margin:0">${items.length} producto${items.length === 1 ? "" : "s"}</h2>
                    <button type="button" class="boton-texto" id="vaciar">Vaciar carrito</button>
                </div>
                ${items.map((p) => {
                    const problema = problemaDe(p);
                    return `
                    <div class="item-carrito">
                        <a class="foto" href="producto.html?id=${p.id_producto}">${imagenProducto(p.imagen_principal, p.nombre)}</a>
                        <div>
                            <a class="nombre" href="producto.html?id=${p.id_producto}">${esc(p.nombre)}</a>
                            <div class="vendedor">Vendido por ${esc(p.vendedor)} · ${precio(p.precio_unitario)} c/u</div>
                            ${problema ? `<div class="error-campo">${esc(problema)}</div>` : ""}
                        </div>
                        <div class="acciones-item" style="display:flex;gap:10px;align-items:center">
                            <div class="selector-cantidad">
                                <button type="button" data-cambiar="${p.id_producto}" data-delta="-1" aria-label="Menos">−</button>
                                <input type="number" min="1" max="${Math.max(1, p.stock_disponible)}" value="${p.cantidad}"
                                       data-cantidad="${p.id_producto}" aria-label="Cantidad de ${esc(p.nombre)}">
                                <button type="button" data-cambiar="${p.id_producto}" data-delta="1" aria-label="Más">+</button>
                            </div>
                            <button type="button" class="boton-texto" data-quitar="${p.id_producto}">Quitar</button>
                        </div>
                        <div class="subtotal">${precio(p.subtotal)}</div>
                    </div>`;
                }).join("")}
            </section>

            <aside class="tarjeta resumen">
                <h2>Resumen</h2>
                <div class="linea"><span>Productos (${unidades})</span><span>${precio(carrito.total)}</span></div>
                <div class="linea"><span>Envío</span><span>Gratis</span></div>
                <div class="linea total"><span>Total</span><span>${precio(carrito.total)}</span></div>
                ${conProblemas.length ? `<div class="mensaje mensaje-aviso" style="margin-top:14px">Ajusta los productos marcados para poder comprar.</div>` : ""}
                <a class="boton boton-bloque boton-grande ${conProblemas.length ? "deshabilitado" : ""}"
                   style="margin-top:14px${conProblemas.length ? ";pointer-events:none;opacity:.55" : ""}"
                   href="checkout.html" ${conProblemas.length ? 'aria-disabled="true"' : ""}>Continuar compra</a>
                <a class="boton boton-secundario boton-bloque" style="margin-top:8px" href="index.html">Seguir comprando</a>
            </aside>
        </div>`;
}

async function cargar() {
    try {
        pintar(await api("GET", "/carrito/"));
    } catch (e) {
        document.getElementById("contenido").innerHTML = `<div class="tarjeta vacio">${esc(e.message)}</div>`;
    }
}

async function cambiarCantidad(idProducto, cantidad) {
    if (cantidad < 1) return;

    try {
        await api("PUT", `/carrito/actualizar/${idProducto}?cantidad=${cantidad}`);
    } catch (e) {
        aviso(e.message, "error");
    }

    await cargar();
}

document.addEventListener("DOMContentLoaded", () => {
    if (!requerirSesion()) return;

    const contenido = document.getElementById("contenido");

    contenido.addEventListener("click", async (e) => {
        const cambiar = e.target.closest("[data-cambiar]");
        if (cambiar) {
            const entrada = contenido.querySelector(`[data-cantidad="${cambiar.dataset.cambiar}"]`);
            const nueva = Number(entrada.value) + Number(cambiar.dataset.delta);
            if (nueva >= 1) await cambiarCantidad(cambiar.dataset.cambiar, nueva);
            return;
        }

        const quitar = e.target.closest("[data-quitar]");
        if (quitar) {
            try {
                await api("DELETE", `/carrito/eliminar/${quitar.dataset.quitar}`);
                aviso("Producto quitado del carrito.");
            } catch (err) {
                aviso(err.message, "error");
            }
            await cargar();
            return;
        }

        if (e.target.id === "vaciar") {
            const ok = await confirmar("¿Quieres quitar todos los productos del carrito?", {
                titulo: "Vaciar carrito", textoBoton: "Vaciar", peligro: true
            });
            if (!ok) return;

            try {
                await api("DELETE", "/carrito/vaciar");
            } catch (err) {
                aviso(err.message, "error");
            }
            await cargar();
        }
    });

    contenido.addEventListener("change", (e) => {
        const entrada = e.target.closest("[data-cantidad]");
        if (!entrada) return;

        const valor = Math.floor(Number(entrada.value));
        if (!valor || valor < 1) {
            entrada.value = 1;
        }
        cambiarCantidad(entrada.dataset.cantidad, Math.max(1, valor || 1));
    });

    cargar();
});
