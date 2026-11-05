"use strict";

function pintarProducto(p) {
    const usuario = Sesion.usuario();
    const propio = usuario && usuario.id_usuario === p.id_vendedor;
    const disponible = p.estado === "PUBLICADO" && p.stock > 0;
    const imagenes = p.imagenes || [];

    document.title = `${p.nombre} | Trama`;
    document.getElementById("migas").innerHTML =
        `<a href="index.html">Inicio</a> › ${esc(p.categoria)} › ${esc(p.nombre)}`;

    let accion;

    if (propio) {
        accion = `
            <div class="mensaje mensaje-info">Este producto es tuyo.</div>
            <a class="boton" href="vender.html?editar=${p.id_producto}">Editar publicación</a>`;
    } else if (!disponible) {
        accion = `<div class="mensaje mensaje-aviso">Este producto no está disponible en este momento.</div>`;
    } else {
        accion = `
            <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
                <div class="selector-cantidad">
                    <button type="button" id="menos" aria-label="Menos">−</button>
                    <input type="number" id="cantidad" value="1" min="1" max="${p.stock}" aria-label="Cantidad">
                    <button type="button" id="mas" aria-label="Más">+</button>
                </div>
                <button type="button" class="boton boton-grande" id="agregar">Agregar al carrito</button>
            </div>
            <button type="button" class="boton boton-turquesa boton-bloque" id="comprar-ahora" style="margin-top:12px">Comprar ahora</button>`;
    }

    document.getElementById("contenido").innerHTML = `
        <article class="detalle-producto">
            <div>
                <div class="galeria-principal" id="foto-principal">
                    ${imagenProducto(imagenes[0] && imagenes[0].ruta, p.nombre)}
                </div>
                ${imagenes.length > 1 ? `
                    <div class="miniaturas">
                        ${imagenes.map((img, i) => `
                            <button type="button" class="${i === 0 ? "activa" : ""}" data-ruta="${esc(img.ruta)}" aria-label="Foto ${i + 1}">
                                <img src="${esc(urlImagen(img.ruta))}" alt="">
                            </button>`).join("")}
                    </div>` : ""}
            </div>

            <div class="info-producto">
                ${etiquetaEstado(p.estado)}
                <h1 style="margin-top:10px">${esc(p.nombre)}</h1>
                <div class="precio-grande">${precio(p.precio)}</div>

                <ul class="lista-datos">
                    <li><span>Condición</span><span>${esc(CONDICIONES[p.condicion] || p.condicion)}</span></li>
                    <li><span>Disponibles</span><span>${p.stock} unidad${p.stock === 1 ? "" : "es"}</span></li>
                    <li><span>Categoría</span><span>${esc(p.categoria)}</span></li>
                    <li><span>Vendedor</span><span>${esc(p.vendedor)}</span></li>
                    <li><span>Publicado</span><span>${fecha(p.fecha_publicacion)}</span></li>
                </ul>

                ${accion}

                <h2 style="font-size:16px;color:var(--azul);margin:26px 0 8px">Descripción</h2>
                <p style="white-space:pre-line;margin:0">${esc(p.descripcion)}</p>
            </div>
        </article>`;

    // Galería
    document.querySelectorAll(".miniaturas button").forEach((b) =>
        b.addEventListener("click", () => {
            document.querySelectorAll(".miniaturas button").forEach((x) => x.classList.remove("activa"));
            b.classList.add("activa");
            document.getElementById("foto-principal").innerHTML = imagenProducto(b.dataset.ruta, p.nombre);
        })
    );

    if (!propio && disponible) {
        const entrada = document.getElementById("cantidad");
        const ajustar = (delta) => {
            const v = Math.min(p.stock, Math.max(1, (Number(entrada.value) || 1) + delta));
            entrada.value = v;
        };

        document.getElementById("menos").addEventListener("click", () => ajustar(-1));
        document.getElementById("mas").addEventListener("click", () => ajustar(1));
        entrada.addEventListener("change", () => ajustar(0));

        document.getElementById("agregar").addEventListener("click", (e) =>
            conBoton(e.currentTarget, () => agregarAlCarrito(p.id_producto, entrada.value), "Agregando...")
        );

        document.getElementById("comprar-ahora").addEventListener("click", async (e) => {
            const ok = await conBoton(e.currentTarget, () => agregarAlCarrito(p.id_producto, entrada.value), "Agregando...");
            if (ok) window.location.href = "carrito.html";
        });
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    const id = Number(parametro("id"));
    const contenido = document.getElementById("contenido");

    if (!id) {
        contenido.innerHTML = `<div class="vacio">Producto no encontrado. <a href="index.html">Volver a la tienda</a></div>`;
        return;
    }

    try {
        const p = await api("GET", `/productos/${id}`, { autenticado: false });

        if (p.estado === "ELIMINADO") {
            contenido.innerHTML = `<div class="vacio">Este producto ya no está publicado. <a href="index.html">Volver a la tienda</a></div>`;
            return;
        }

        pintarProducto(p);
    } catch (e) {
        contenido.innerHTML = `<div class="vacio">${esc(e.message)} <a href="index.html">Volver a la tienda</a></div>`;
    }
});
