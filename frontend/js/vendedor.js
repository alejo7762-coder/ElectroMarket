"use strict";

/* Perfil público del vendedor: datos, fiabilidad, reseñas y productos */

document.addEventListener("DOMContentLoaded", async () => {
    const id = Number(parametro("id"));
    const perfil = document.getElementById("perfil");

    if (!id) {
        perfil.innerHTML = `<div class="vacio">Vendedor no encontrado. <a href="index.html">Volver a la tienda</a></div>`;
        return;
    }

    try {
        const v = await api("GET", `/vendedores/${id}`, { autenticado: false });
        document.title = `${v.nombre} | ElectroMarket`;
        document.getElementById("migas").innerHTML = `<a href="index.html">Inicio</a> › Vendedor › ${esc(v.nombre)}`;
        perfil.innerHTML = tarjetaVendedor(v, { enlace: false });
    } catch (e) {
        perfil.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
        return;
    }

    api("GET", `/vendedores/${id}/resenas`, { autenticado: false })
        .then((r) => {
            document.getElementById("resenas").innerHTML =
                `<h2 class="titulo-tarjeta" data-icono="estrella">Opiniones sobre el vendedor</h2>
                 ${distribucionEstrellas(r)}${listaResenas(r.resenas, { campo: "calificacion_vendedor", mostrarProducto: true })}`;
        })
        .catch((e) => { document.getElementById("resenas").innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`; });

    api("GET", `/productos/?id_vendedor=${id}`, { autenticado: false })
        .then(({ productos }) => {
            document.getElementById("productos").innerHTML = productos.length
                ? productos.map(tarjetaProducto).join("")
                : `<div class="vacio">Este vendedor no tiene productos publicados en este momento.</div>`;
        })
        .catch((e) => { document.getElementById("productos").innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`; });
});
