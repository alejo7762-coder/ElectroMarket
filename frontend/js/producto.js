"use strict";

const NIVEL_CONDICION = { COMO_NUEVO: 3, BUENO: 2, ACEPTABLE: 1 };

function panelVerificacion(p) {
    const v = p.verificacion || { nivel: "SIN_VERIFICAR", puntaje: 0, criterios: [], faltantes: [] };
    const usuario = Sesion.usuario();
    const propio = Boolean(usuario && usuario.id_usuario === p.id_vendedor);
    const nivel = NIVEL_CONDICION[p.condicion] || 0;
    const tono = v.puntaje >= 80 ? "alto" : v.puntaje >= 50 ? "medio" : "bajo";

    return `
        <section class="panel-verificacion" aria-label="Estado del producto">
            <div class="panel-verificacion-cabecera">
                ${insigniaVerificacion(v.nivel)}
                <span class="puntaje-estado">${v.puntaje}<small>/100</small></span>
            </div>

            <div class="escala-condicion" aria-label="Condición: ${esc(CONDICIONES[p.condicion] || p.condicion)}">
                ${["Aceptable", "Buen estado", "Como nuevo"].map((t, i) =>
                    `<span class="${i < nivel ? "activo" : ""}${i === nivel - 1 ? " actual" : ""}">${t}</span>`).join("")}
            </div>

            <div class="barra-puntaje barra-${tono}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v.puntaje}"
                 aria-label="Puntaje de estado"><span style="width:${v.puntaje}%"></span></div>

            ${v.criterios.length ? `
                <ul class="checklist-resultado">
                    ${v.criterios.map((c) => `
                        <li class="${c.cumple ? "cumple" : "no-cumple"}">
                            ${icono(c.cumple ? "check" : "cerrar")}
                            ${esc(c.texto)}${c.esencial ? ' <em>esencial</em>' : ""}
                        </li>`).join("")}
                </ul>` : ""}

            <div class="fotos-verificacion ${v.total_fotos >= v.fotos_requeridas ? "cumple" : "no-cumple"}">
                ${icono("camara")}${v.total_fotos} de ${v.fotos_requeridas} fotos mínimas
            </div>

            ${v.defectos ? `
                <div class="defectos ${v.sin_defectos ? "defectos-ninguno" : ""}">
                    <strong>${v.sin_defectos ? "Sin defectos declarados" : "Defectos declarados por el vendedor"}</strong>
                    ${v.sin_defectos ? "" : `<p>${esc(v.defectos)}</p>`}
                </div>` : ""}

            ${panelIA(p.inspeccion_ia, { vistaComprador: !propio })}

            ${v.faltantes.length ? `
                <details class="faltantes">
                    <summary>¿Por qué no está verificado?</summary>
                    <ul>${v.faltantes.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
                </details>` : ""}
        </section>`;
}

/* ------------------------------------------------------------------ */
/* Vendedor y reseñas                                                  */
/* ------------------------------------------------------------------ */

async function cargarVendedor(idVendedor) {
    const destino = document.getElementById("vendedor-producto");
    try {
        const v = await api("GET", `/vendedores/${idVendedor}`, { autenticado: false });
        destino.innerHTML = `<h2 class="titulo-tarjeta" data-icono="usuario">Sobre el vendedor</h2>${tarjetaVendedor(v)}`;
    } catch (e) {
        destino.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
    }
}

async function cargarResenas(idProducto) {
    const destino = document.getElementById("resenas-producto");
    try {
        const r = await api("GET", `/productos/${idProducto}/resenas`, { autenticado: false });
        destino.innerHTML = `<h2 class="titulo-tarjeta" data-icono="estrella">Reseñas del producto</h2>${distribucionEstrellas(r)}${listaResenas(r.resenas)}`;
    } catch (e) {
        destino.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
    }
}

function pintarProducto(p) {
    const usuario = Sesion.usuario();
    const propio = usuario && usuario.id_usuario === p.id_vendedor;
    const disponible = p.estado === "PUBLICADO" && p.stock > 0;
    const imagenes = p.imagenes || [];

    document.title = `${p.nombre} | ElectroMarket`;
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
            <div class="u-fila u-gap-12 u-envolver">
                <div class="selector-cantidad">
                    <button type="button" id="menos" aria-label="Menos">−</button>
                    <input type="number" id="cantidad" value="1" min="1" max="${p.stock}" aria-label="Cantidad">
                    <button type="button" id="mas" aria-label="Más">+</button>
                </div>
                <button type="button" class="boton boton-grande" id="agregar">Agregar al carrito</button>
            </div>
            <button type="button" class="boton boton-turquesa boton-bloque u-mt-12" id="comprar-ahora">Comprar ahora</button>`;
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
                <h1 class="u-mt-10">${esc(p.nombre)}</h1>
                <div class="precio-grande">${precio(p.precio)}</div>

                <ul class="lista-datos">
                    <li><span>${icono("estrella")}Condición</span><span>${esc(CONDICIONES[p.condicion] || p.condicion)}</span></li>
                    <li><span>${icono("inventario")}Disponibles</span><span>${p.stock} unidad${p.stock === 1 ? "" : "es"}</span></li>
                    <li><span>${icono("etiqueta")}Categoría</span><span>${esc(p.categoria)}</span></li>
                    <li><span>${icono("usuario")}Vendedor</span><span><a href="vendedor.html?id=${p.id_vendedor}">${esc(p.vendedor)}</a></span></li>
                    <li><span>${icono("estrella")}Calificación</span><span>${resumenEstrellas(p.calificacion)}</span></li>
                    <li><span>${icono("calendario")}Publicado</span><span>${fecha(p.fecha_publicacion)}</span></li>
                </ul>

                ${panelVerificacion(p)}

                ${accion}

                <h2 class="subtitulo-bloque" data-icono="info">Descripción</h2>
                <p class="u-pre-linea u-m-0">${esc(p.descripcion)}</p>
            </div>
        </article>

        <div class="producto-secundario">
            <section class="tarjeta" id="vendedor-producto" aria-label="Información del vendedor"><div class="cargando">Cargando vendedor...</div></section>
            <section class="tarjeta" id="resenas-producto" aria-label="Reseñas del producto"><div class="cargando">Cargando reseñas...</div></section>
        </div>`;

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
        cargarVendedor(p.id_vendedor);
        cargarResenas(p.id_producto);
    } catch (e) {
        contenido.innerHTML = `<div class="vacio">${esc(e.message)} <a href="index.html">Volver a la tienda</a></div>`;
    }
});
