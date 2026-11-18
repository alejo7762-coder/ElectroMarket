"use strict";

/* Vendedor, fiabilidad y reseñas: compartido por producto.html y vendedor.html */

function tarjetaVendedor(v, { enlace = true } = {}) {
    const f = v.fiabilidad;
    const tono = f.nivel === "ALTA" ? "alto" : f.nivel === "BAJA" ? "bajo" : "medio";

    return `
        <div class="vendedor-cabecera">
            <div class="avatar" aria-hidden="true">${iniciales(v.nombre)}</div>
            <div>
                <h2 class="u-m-0">${esc(v.nombre)}</h2>
                <div class="ayuda u-m-0">Miembro desde ${fecha(v.miembro_desde)}</div>
                ${resumenEstrellas(v.calificacion_vendedor)}
            </div>
        </div>
        <div class="vendedor-datos">
            <div><strong>${v.ventas_entregadas}</strong><span>ventas entregadas</span></div>
            <div><strong>${v.productos_publicados}</strong><span>productos publicados</span></div>
            <div><strong>${v.calificacion_vendedor.total}</strong><span>reseñas</span></div>
        </div>
        <div class="fiabilidad">
            <div class="u-fila-entre"><strong>¿Qué tan confiable es?</strong>${insigniaFiabilidad(f)}</div>
            <div class="barra-puntaje barra-${tono}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${f.indice}"
                 aria-label="Índice de fiabilidad"><span style="width:${f.indice}%"></span></div>
            <ul class="fiabilidad-factores">
                ${f.factores.map((x) => `
                    <li><span>${esc(x.factor)} <small>${esc(x.detalle)}</small></span>
                        <span class="u-negrita">${x.puntos.toLocaleString("es-CO")} / ${x.maximo}</span></li>`).join("")}
            </ul>
            <small class="ayuda">Calculado con las ventas y reseñas reales del vendedor en ElectroMarket.</small>
        </div>
        ${enlace ? `<a class="boton boton-secundario boton-bloque u-mt-10" href="vendedor.html?id=${v.id_vendedor}">Ver perfil del vendedor</a>` : ""}`;
}

function distribucionEstrellas(resumen) {
    return `
        <div class="resumen-resenas">
            <div class="promedio-resenas">
                <strong>${resumen.promedio == null ? "–" : resumen.promedio.toLocaleString("es-CO", { maximumFractionDigits: 1 })}</strong>
                ${estrellas(resumen.promedio, { tamano: "estrellas-grandes" })}
                <small>${resumen.total} reseña${resumen.total === 1 ? "" : "s"}</small>
            </div>
            <ul class="distribucion">
                ${[5, 4, 3, 2, 1].map((n) => {
                    const cantidad = resumen.distribucion[n] || 0;
                    const ancho = resumen.total ? Math.round(cantidad / resumen.total * 100) : 0;
                    return `<li><span>${n} ${ESTRELLA_SVG}</span><span class="barra-dist"><span style="width:${ancho}%"></span></span><span>${cantidad}</span></li>`;
                }).join("")}
            </ul>
        </div>`;
}

function listaResenas(resenas, { campo = "calificacion_producto", mostrarProducto = false } = {}) {
    if (!resenas.length) {
        return `<p class="ayuda">Todavía no hay reseñas. Solo los compradores con una compra entregada pueden calificar.</p>`;
    }
    return `<ul class="lista-resenas">${resenas.map((r) => `
        <li class="resena">
            <div class="u-fila-entre u-gap-10 u-envolver">
                <span class="u-fila u-gap-10"><span class="avatar avatar-chico" aria-hidden="true">${iniciales(r.comprador)}</span>
                    <strong>${esc(r.comprador)}</strong>
                    <span class="estado estado-ok">${icono("check")} Compra verificada</span></span>
                <small class="ayuda u-m-0">${fecha(r.fecha)}${r.editada ? " · editada" : ""}</small>
            </div>
            <div class="resena-calificaciones">
                <span>Producto ${estrellas(r.calificacion_producto)}</span>
                <span>Vendedor ${estrellas(r.calificacion_vendedor)}</span>
            </div>
            ${mostrarProducto ? `<div class="ayuda u-m-0">Sobre <a href="producto.html?id=${r.id_producto}">${esc(r.producto)}</a></div>` : ""}
            ${r.comentario ? `<p class="u-pre-linea">${esc(r.comentario)}</p>` : ""}
        </li>`).join("")}</ul>`;
}
