"use strict";

let todosLosProductos = [];
let categoriaActiva = null;

const VACIO = (texto) => `
    <div class="vacio" style="grid-column:1/-1">
        ${ICONOS.caja}
        <p>${esc(texto)}</p>
    </div>`;

function normalizar(texto) {
    return String(texto || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "");
}

function pintarCarrusel(productos) {
    const pista = document.getElementById("carrusel-pista");

    if (!productos.length) {
        pista.innerHTML = `<div class="vacio" style="color:#fff;width:100%">Aún no hay productos publicados.
            <br><a href="vender.html" style="color:#fff;font-weight:700">¡Publica el primero!</a></div>`;
        document.querySelectorAll(".flecha-carrusel").forEach((b) => b.classList.add("oculto"));
        return;
    }

    pista.innerHTML = productos.map(tarjetaProducto).join("");
}

function pintarCatalogo() {
    const rejilla = document.getElementById("rejilla-catalogo");
    const lista = categoriaActiva
        ? todosLosProductos.filter((p) => p.id_categoria === categoriaActiva)
        : todosLosProductos;

    rejilla.innerHTML = lista.length
        ? lista.map(tarjetaProducto).join("")
        : VACIO("No hay productos en esta categoría.");
}

function pintarFiltros(categorias) {
    const filtros = document.getElementById("filtros");

    const chips = [`<button type="button" class="chip activo" data-categoria="">Todas</button>`]
        .concat(categorias.map((c) =>
            `<button type="button" class="chip" data-categoria="${c.id_categoria}">${esc(c.nombre)}</button>`
        ));

    filtros.innerHTML = chips.join("");

    filtros.addEventListener("click", (e) => {
        const chip = e.target.closest(".chip");
        if (!chip) return;

        filtros.querySelectorAll(".chip").forEach((c) => c.classList.remove("activo"));
        chip.classList.add("activo");
        categoriaActiva = chip.dataset.categoria ? Number(chip.dataset.categoria) : null;
        pintarCatalogo();
    });
}

function pintarResultados(termino) {
    const palabras = normalizar(termino).split(/\s+/).filter(Boolean);

    const encontrados = todosLosProductos.filter((p) => {
        const texto = normalizar(`${p.nombre} ${p.descripcion} ${p.categoria}`);
        return palabras.every((palabra) => texto.includes(palabra));
    });

    document.getElementById("seccion-resultados").classList.remove("oculto");
    document.getElementById("seccion-destacados").classList.add("oculto");
    document.getElementById("titulo-resultados").textContent = `Resultados para “${termino}”`;
    document.getElementById("subtitulo-resultados").innerHTML =
        `${encontrados.length} producto${encontrados.length === 1 ? "" : "s"} encontrado${encontrados.length === 1 ? "" : "s"} · <a href="index.html">Ver todo</a>`;

    document.getElementById("rejilla-resultados").innerHTML = encontrados.length
        ? encontrados.map(tarjetaProducto).join("")
        : VACIO("No encontramos productos con esa búsqueda. Prueba con otras palabras.");
}

function configurarFlechas() {
    const pista = document.getElementById("carrusel-pista");
    const paso = () => pista.clientWidth * 0.8;

    document.getElementById("carrusel-derecha").addEventListener("click", () => {
        const alFinal = pista.scrollLeft + pista.clientWidth >= pista.scrollWidth - 4;
        pista.scrollBy({ left: alFinal ? -pista.scrollWidth : paso() });
    });

    document.getElementById("carrusel-izquierda").addEventListener("click", () => {
        pista.scrollBy({ left: -paso() });
    });
}

async function iniciar() {
    configurarFlechas();
    document.querySelector(".banner .rayo").innerHTML = ICONOS.rayo;

    try {
        const [respuesta, categorias] = await Promise.all([
            api("GET", "/productos/", { autenticado: false }),
            api("GET", "/categorias/", { autenticado: false })
        ]);

        todosLosProductos = respuesta.productos || [];

        // Destacados: los más recientes con foto primero
        const destacados = [...todosLosProductos]
            .sort((a, b) => Number(Boolean(b.imagen_principal)) - Number(Boolean(a.imagen_principal)))
            .slice(0, 10);

        pintarCarrusel(destacados);
        pintarFiltros(categorias.filter((c) => todosLosProductos.some((p) => p.id_categoria === c.id_categoria)));
        pintarCatalogo();

        const termino = (parametro("q") || "").trim();
        if (termino) pintarResultados(termino);

    } catch (e) {
        document.getElementById("carrusel-pista").innerHTML =
            `<div class="vacio" style="color:#fff;width:100%">${esc(e.message)}</div>`;
        document.getElementById("rejilla-catalogo").innerHTML = "";
    }
}

document.addEventListener("DOMContentLoaded", iniciar);
