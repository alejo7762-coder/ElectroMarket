"use strict";

const MAX_FOTOS = 5;
const MAX_TAMANO = 5 * 1024 * 1024;
const FORMATOS = ["image/jpeg", "image/png", "image/webp"];

let productoEditado = null;   // producto en edición (o null si es nuevo)
let fotosNuevas = [];         // archivos elegidos por el usuario

/* ------------------------------------------------------------------ */
/* Fotos                                                               */
/* ------------------------------------------------------------------ */

function fotosPermitidas() {
    const actuales = productoEditado ? (productoEditado.imagenes || []).length : 0;
    return MAX_FOTOS - actuales;
}

function elegirFotos(e) {
    const archivos = Array.from(e.target.files || []);
    const errores = [];
    const libres = fotosPermitidas();

    fotosNuevas = [];

    for (const archivo of archivos) {
        if (!FORMATOS.includes(archivo.type)) {
            errores.push(`${archivo.name}: formato no permitido.`);
        } else if (archivo.size > MAX_TAMANO) {
            errores.push(`${archivo.name}: supera los 5 MB.`);
        } else if (fotosNuevas.length >= libres) {
            errores.push(`${archivo.name}: solo se permiten ${MAX_FOTOS} fotos por producto.`);
        } else {
            fotosNuevas.push(archivo);
        }
    }

    const caja = document.getElementById("previsualizaciones");
    caja.innerHTML = "";

    fotosNuevas.forEach((archivo) => {
        const img = document.createElement("img");
        img.alt = archivo.name;
        img.src = URL.createObjectURL(archivo);
        img.onload = () => URL.revokeObjectURL(img.src);
        caja.appendChild(img);
    });

    mostrarMensaje(
        document.getElementById("msg-producto"),
        errores.length ? "Algunas fotos no se agregarán:" : "",
        "aviso",
        errores
    );
}

async function subirFotos(idProducto) {
    const fallidas = [];

    for (const archivo of fotosNuevas) {
        const datos = new FormData();
        datos.append("archivo", archivo);

        try {
            await api("POST", `/productos/${idProducto}/imagenes`, { formulario: datos });
        } catch (e) {
            fallidas.push(`${archivo.name}: ${e.message}`);
        }
    }

    return fallidas;
}

function pintarFotosActuales() {
    const bloque = document.getElementById("bloque-fotos-actuales");
    const contenedor = document.getElementById("fotos-actuales");
    const imagenes = productoEditado ? productoEditado.imagenes || [] : [];

    bloque.classList.toggle("oculto", !productoEditado);

    contenedor.innerHTML = imagenes.length
        ? imagenes.map((img) => `
            <div class="foto-item ${img.es_principal ? "principal" : ""}">
                <img src="${esc(urlImagen(img.ruta))}" alt="">
                <div class="acciones">
                    ${img.es_principal
                        ? `<span class="estado estado-proceso" style="text-align:center">Principal</span>`
                        : `<button type="button" class="boton boton-secundario boton-chico" data-principal="${img.id_imagen}">Hacer principal</button>`}
                    <button type="button" class="boton boton-secundario boton-chico" data-borrar-foto="${img.id_imagen}">Eliminar</button>
                </div>
            </div>`).join("")
        : `<p class="ayuda">Este producto no tiene fotos.</p>`;

    const libres = fotosPermitidas();
    const entrada = document.getElementById("fotos");
    entrada.disabled = libres <= 0;
    document.getElementById("ayuda-fotos").textContent = libres > 0
        ? `Puedes agregar ${libres} foto${libres === 1 ? "" : "s"} más (JPG, PNG o WEBP, máximo 5 MB).`
        : "Ya tienes el máximo de 5 fotos. Elimina alguna para agregar otra.";
}

async function accionesFotos(e) {
    const principal = e.target.closest("[data-principal]");
    const borrar = e.target.closest("[data-borrar-foto]");
    if (!principal && !borrar) return;

    const id = productoEditado.id_producto;

    try {
        if (principal) {
            await api("PATCH", `/productos/${id}/imagenes/${principal.dataset.principal}/principal`);
            aviso("Foto principal actualizada.", "exito");
        } else {
            const ok = await confirmar("¿Eliminar esta foto?", { titulo: "Eliminar foto", textoBoton: "Eliminar", peligro: true });
            if (!ok) return;
            await api("DELETE", `/productos/${id}/imagenes/${borrar.dataset.borrarFoto}`);
            aviso("Foto eliminada.", "exito");
        }

        productoEditado = await api("GET", `/productos/${id}`, { autenticado: false });
        pintarFotosActuales();
        cargarMisProductos();
    } catch (err) {
        aviso(err.message, "error");
    }
}

/* ------------------------------------------------------------------ */
/* Formulario                                                          */
/* ------------------------------------------------------------------ */

function leerFormulario(form) {
    return {
        id_categoria: Number(form.id_categoria.value),
        nombre: form.nombre.value.trim(),
        descripcion: form.descripcion.value.trim(),
        precio: Number(form.precio.value),
        stock: Number(form.stock.value),
        condicion: form.condicion.value
    };
}

function validarFormulario(d) {
    const errores = [];
    if (d.nombre.length < 2) errores.push("Escribe el título de la publicación.");
    if (!d.id_categoria) errores.push("Selecciona una categoría.");
    if (!d.descripcion) errores.push("Escribe una descripción.");
    if (!(d.precio > 0)) errores.push("El precio debe ser mayor que cero.");
    if (!Number.isInteger(d.stock) || d.stock < 0) errores.push("Las unidades deben ser un número entero (0 o más).");
    return errores;
}

async function guardar(e) {
    e.preventDefault();

    const form = e.target;
    const caja = document.getElementById("msg-producto");
    const datos = leerFormulario(form);
    const errores = validarFormulario(datos);

    if (errores.length) {
        mostrarMensaje(caja, "Revisa los datos:", "error", errores);
        caja.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }

    await conBoton(document.getElementById("boton-guardar"), async () => {
        try {
            let idProducto;

            if (productoEditado) {
                await api("PUT", `/productos/${productoEditado.id_producto}`, { cuerpo: datos });
                idProducto = productoEditado.id_producto;
            } else {
                idProducto = (await api("POST", "/productos/publicar", { cuerpo: datos })).id_producto;
            }

            const fallidas = await subirFotos(idProducto);

            if (fallidas.length) {
                mostrarMensaje(caja, "El producto se guardó, pero algunas fotos no se pudieron subir:", "aviso", fallidas);
            } else if (productoEditado) {
                mostrarMensaje(caja, "Los cambios se guardaron correctamente.", "exito");
            } else {
                form.reset();
                form.stock.value = 1;
                form.condicion.value = "BUENO";
                document.getElementById("contador-descripcion").textContent = "0";
                mostrarMensaje(caja, "", "exito");
                aviso("¡Tu artículo ya está publicado!", "exito");
            }

            fotosNuevas = [];
            document.getElementById("fotos").value = "";
            document.getElementById("previsualizaciones").innerHTML = "";

            if (productoEditado) {
                productoEditado = await api("GET", `/productos/${idProducto}`, { autenticado: false });
                pintarFotosActuales();
            }

            cargarMisProductos();

        } catch (err) {
            mostrarMensaje(caja, err.message, "error");
        }
    }, productoEditado ? "Guardando..." : "Publicando...");
}

async function prepararEdicion(id) {
    const caja = document.getElementById("msg-producto");

    try {
        const p = await api("GET", `/productos/${id}`, { autenticado: false });
        const usuario = Sesion.usuario();

        if (!usuario || p.id_vendedor !== usuario.id_usuario || p.estado === "ELIMINADO") {
            mostrarMensaje(caja, "No puedes editar este producto.", "error");
            return;
        }

        productoEditado = p;

        const form = document.getElementById("form-producto");
        form.nombre.value = p.nombre;
        form.id_categoria.value = String(p.id_categoria);
        form.descripcion.value = p.descripcion;
        form.precio.value = Math.round(p.precio);
        form.stock.value = p.stock;
        form.condicion.value = p.condicion;
        document.getElementById("contador-descripcion").textContent = p.descripcion.length;

        document.getElementById("titulo-formulario").textContent = "Editar publicación";
        document.getElementById("subtitulo-formulario").innerHTML =
            `${etiquetaEstado(p.estado)} <a href="producto.html?id=${p.id_producto}">Ver cómo se ve en la tienda</a>`;
        document.getElementById("boton-guardar").textContent = "Guardar cambios";
        document.getElementById("cancelar-edicion").classList.remove("oculto");
        document.querySelector("label[for=fotos]").textContent = "Agregar fotografías";

        pintarFotosActuales();
    } catch (e) {
        mostrarMensaje(caja, e.message, "error");
    }
}

/* ------------------------------------------------------------------ */
/* Mis productos                                                       */
/* ------------------------------------------------------------------ */

async function cargarMisProductos() {
    const destino = document.getElementById("tabla-productos");

    try {
        const { productos } = await api("GET", "/mis-productos/");

        if (!productos.length) {
            destino.innerHTML = `<div class="vacio">${ICONOS.caja}<p>Aún no has publicado productos.</p></div>`;
            return;
        }

        destino.innerHTML = `
            <div class="tabla-envoltura">
                <table class="tabla">
                    <thead>
                        <tr><th></th><th>Producto</th><th class="numero">Precio</th><th class="numero">Unidades</th><th>Estado</th><th>Acciones</th></tr>
                    </thead>
                    <tbody>
                        ${productos.map((p) => `
                            <tr>
                                <td style="width:64px"><div class="miniatura">${imagenProducto(p.imagen_principal, p.nombre)}</div></td>
                                <td>
                                    <a href="producto.html?id=${p.id_producto}">${esc(p.nombre)}</a>
                                    <div class="ayuda">${esc(p.categoria)} · ${p.total_imagenes} foto${p.total_imagenes === 1 ? "" : "s"}</div>
                                </td>
                                <td class="numero">${precio(p.precio)}</td>
                                <td class="numero">${p.stock}</td>
                                <td>${etiquetaEstado(p.estado)}</td>
                                <td>
                                    <div class="grupo-botones">
                                        <a class="boton boton-secundario boton-chico" href="vender.html?editar=${p.id_producto}">Editar</a>
                                        ${p.estado === "PUBLICADO"
                                            ? `<button type="button" class="boton boton-secundario boton-chico" data-accion="PAUSAR" data-id="${p.id_producto}">Pausar</button>`
                                            : `<button type="button" class="boton boton-secundario boton-chico" data-accion="REACTIVAR" data-id="${p.id_producto}" ${p.stock > 0 ? "" : 'disabled title="Agrega unidades para reactivarlo"'}>Reactivar</button>`}
                                        <button type="button" class="boton boton-secundario boton-chico" data-accion="ELIMINAR" data-id="${p.id_producto}">Eliminar</button>
                                    </div>
                                </td>
                            </tr>`).join("")}
                    </tbody>
                </table>
            </div>`;
    } catch (e) {
        destino.innerHTML = `<div class="mensaje mensaje-error">${esc(e.message)}</div>`;
    }
}

async function accionProducto(e) {
    const boton = e.target.closest("[data-accion]");
    if (!boton) return;

    const accion = boton.dataset.accion;

    if (accion === "ELIMINAR") {
        const ok = await confirmar(
            "La publicación dejará de aparecer en la tienda. Esta acción no se puede deshacer.",
            { titulo: "Eliminar producto", textoBoton: "Eliminar", peligro: true }
        );
        if (!ok) return;
    }

    try {
        await api("PATCH", `/productos/${boton.dataset.id}/estado?accion=${accion}`);
        aviso({ PAUSAR: "Producto pausado.", REACTIVAR: "Producto publicado de nuevo.", ELIMINAR: "Producto eliminado." }[accion], "exito");

        if (accion === "ELIMINAR" && productoEditado && productoEditado.id_producto === Number(boton.dataset.id)) {
            window.location.href = "vender.html#mis-productos";
            return;
        }
    } catch (err) {
        aviso(err.message, "error");
    }

    cargarMisProductos();
}

/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", async () => {
    if (!requerirSesion()) return;

    const form = document.getElementById("form-producto");

    form.addEventListener("submit", guardar);
    document.getElementById("fotos").addEventListener("change", elegirFotos);
    document.getElementById("fotos-actuales").addEventListener("click", accionesFotos);
    document.getElementById("tabla-productos").addEventListener("click", accionProducto);
    form.descripcion.addEventListener("input", () => {
        document.getElementById("contador-descripcion").textContent = form.descripcion.value.length;
    });

    try {
        const categorias = await api("GET", "/categorias/", { autenticado: false });
        form.id_categoria.innerHTML = `<option value="">Selecciona una categoría</option>` +
            categorias.map((c) => `<option value="${c.id_categoria}">${esc(c.nombre)}</option>`).join("");
    } catch (e) {
        mostrarMensaje(document.getElementById("msg-producto"), "No se pudieron cargar las categorías: " + e.message, "error");
    }

    const editar = Number(parametro("editar"));
    if (editar) await prepararEdicion(editar);

    cargarMisProductos();

    if (window.location.hash === "#mis-productos") {
        document.getElementById("mis-productos").scrollIntoView();
    }
});
