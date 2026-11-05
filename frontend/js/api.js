/* =====================================================================
   Trama - Funciones compartidas por todas las páginas
   - Comunicación con la API (fetch + token JWT)
   - Sesión del usuario
   - Encabezado, pie, avisos y ventanas modales
   - Formato de precios, fechas y estados
   ===================================================================== */

"use strict";

const CLAVE_TOKEN = "trama_token";
const CLAVE_USUARIO = "trama_usuario";

/* ------------------------------------------------------------------ */
/* Almacenamiento seguro (algunos navegadores lo bloquean)             */
/* ------------------------------------------------------------------ */

const almacen = {
    leer(clave) {
        try {
            return localStorage.getItem(clave);
        } catch (e) {
            return null;
        }
    },
    guardar(clave, valor) {
        try {
            localStorage.setItem(clave, valor);
        } catch (e) {
            /* sin almacenamiento: la sesión dura lo que la pestaña */
        }
    },
    borrar(clave) {
        try {
            localStorage.removeItem(clave);
        } catch (e) {
            /* nada */
        }
    }
};

/* ------------------------------------------------------------------ */
/* Sesión                                                              */
/* ------------------------------------------------------------------ */

const Sesion = {
    token() {
        return almacen.leer(CLAVE_TOKEN);
    },

    usuario() {
        try {
            return JSON.parse(almacen.leer(CLAVE_USUARIO) || "null");
        } catch (e) {
            return null;
        }
    },

    activa() {
        return Boolean(this.token());
    },

    iniciar(token, usuario) {
        almacen.guardar(CLAVE_TOKEN, token);
        almacen.guardar(CLAVE_USUARIO, JSON.stringify(usuario));
    },

    actualizarUsuario(datos) {
        const actual = this.usuario() || {};
        almacen.guardar(CLAVE_USUARIO, JSON.stringify({ ...actual, ...datos }));
    },

    cerrar() {
        almacen.borrar(CLAVE_TOKEN);
        almacen.borrar(CLAVE_USUARIO);
    }
};

/* ------------------------------------------------------------------ */
/* Errores de la API                                                   */
/* ------------------------------------------------------------------ */

class ErrorApi extends Error {
    constructor(status, mensaje, datos) {
        super(mensaje);
        this.status = status;
        this.datos = datos;
    }
}

const NOMBRES_CAMPOS = {
    nombre: "Nombre",
    apellido: "Apellido",
    correo: "Correo electrónico",
    contrasena: "Contraseña",
    contrasena_actual: "Contraseña actual",
    contrasena_nueva: "Nueva contraseña",
    telefono: "Celular",
    fecha_nacimiento: "Fecha de nacimiento",
    genero: "Género",
    direccion: "Dirección",
    ciudad: "Ciudad",
    departamento: "Departamento",
    codigo_postal: "Código postal",
    descripcion: "Descripción",
    precio: "Precio",
    stock: "Unidades disponibles",
    condicion: "Condición",
    id_categoria: "Categoría",
    numero_tarjeta: "Número de tarjeta",
    motivo: "Motivo",
    productos: "Productos",
    cantidad: "Cantidad",
    transportadora: "Transportadora",
    observacion: "Observación",
    id_direccion: "Dirección de entrega"
};

function traducirMensaje(msg) {
    if (!msg) return "Dato no válido.";

    const reglas = [
        [/^Value error, /, ""],
        [/^Field required$/, "es obligatorio."],
        [/String should have at least (\d+) characters?/, "debe tener al menos $1 caracteres."],
        [/String should have at most (\d+) characters?/, "debe tener como máximo $1 caracteres."],
        [/value is not a valid email address.*/, "no es un correo válido."],
        [/Input should be greater than or equal to (\S+)/, "debe ser mayor o igual a $1."],
        [/Input should be greater than (\S+)/, "debe ser mayor que $1."],
        [/Input should be a valid integer.*/, "debe ser un número entero."],
        [/Input should be a valid (number|decimal).*/, "debe ser un número."],
        [/Input should be a valid string/, "es obligatorio."],
        [/Input should be a valid date.*/, "no es una fecha válida."],
        [/String should match pattern.*/, "no tiene un formato válido."],
        [/Input should be .*/, "tiene un valor no permitido."],
        [/List should have at least 1 item.*/, "debe tener al menos un elemento."]
    ];

    for (const [patron, reemplazo] of reglas) {
        if (patron.test(msg)) {
            return msg.replace(patron, reemplazo);
        }
    }

    return msg;
}

function mensajeDeError(status, cuerpo) {
    const detalle = cuerpo && cuerpo.detail;

    if (Array.isArray(detalle)) {
        return detalle
            .map((e) => {
                const campo = (e.loc || []).filter((p) => typeof p === "string" && p !== "body").pop();
                const texto = traducirMensaje(e.msg);

                if (campo && !texto.startsWith("Debes") && !texto.startsWith("La ")) {
                    return `${NOMBRES_CAMPOS[campo] || campo}: ${texto}`;
                }

                return texto;
            })
            .join(" ");
    }

    if (detalle && typeof detalle === "object") {
        return detalle.mensaje || "No fue posible completar la operación.";
    }

    if (typeof detalle === "string") {
        return detalle;
    }

    if (status === 0) {
        return "No hay conexión con el servidor.";
    }

    return "Ocurrió un error inesperado. Intenta de nuevo.";
}

/* ------------------------------------------------------------------ */
/* Cliente de la API                                                   */
/* ------------------------------------------------------------------ */

async function api(metodo, ruta, opciones = {}) {
    const { cuerpo, formulario, autenticado = true } = opciones;
    const cabeceras = {};

    if (autenticado && Sesion.token()) {
        cabeceras.Authorization = `Bearer ${Sesion.token()}`;
    }

    let body;

    if (formulario) {
        body = formulario;
    } else if (cuerpo !== undefined) {
        cabeceras["Content-Type"] = "application/json";
        body = JSON.stringify(cuerpo);
    }

    let respuesta;

    try {
        respuesta = await fetch(ruta, { method: metodo, headers: cabeceras, body });
    } catch (e) {
        throw new ErrorApi(0, "No hay conexión con el servidor.");
    }

    let datos = null;
    const tipo = respuesta.headers.get("content-type") || "";

    if (tipo.includes("application/json")) {
        datos = await respuesta.json();
    }

    if (respuesta.ok) {
        return datos;
    }

    // Sesión vencida o inválida en una ruta protegida
    if (respuesta.status === 401 && autenticado && Sesion.activa() && !ruta.startsWith("/usuarios/login")) {
        Sesion.cerrar();
        irAIngreso("Tu sesión expiró. Ingresa de nuevo.");
        throw new ErrorApi(401, "Tu sesión expiró.");
    }

    // 402 (pago rechazado) trae datos útiles en el cuerpo
    throw new ErrorApi(respuesta.status, mensajeDeError(respuesta.status, datos), datos);
}

/* ------------------------------------------------------------------ */
/* Navegación                                                          */
/* ------------------------------------------------------------------ */

function parametro(nombre) {
    return new URLSearchParams(window.location.search).get(nombre);
}

function paginaActual() {
    const partes = window.location.pathname.split("/");
    return (partes.pop() || "index.html") + window.location.search;
}

function destinoSeguro(valor) {
    // Solo páginas propias (evita redirecciones a otros sitios)
    if (valor && /^[a-z_]+\.html(\?[\w=&%.-]*)?$/i.test(valor)) {
        return valor;
    }
    return "index.html";
}

function irAIngreso(mensaje) {
    const volver = encodeURIComponent(paginaActual());
    const extra = mensaje ? `&mensaje=${encodeURIComponent(mensaje)}` : "";
    window.location.href = `login.html?volver=${volver}${extra}`;
}

function requerirSesion() {
    if (!Sesion.activa()) {
        irAIngreso("Ingresa para continuar.");
        return false;
    }
    return true;
}

/* ------------------------------------------------------------------ */
/* Formato                                                             */
/* ------------------------------------------------------------------ */

function esc(valor) {
    return String(valor ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function precio(valor) {
    const numero = Number(valor || 0);
    return "$" + numero.toLocaleString("es-CO", { maximumFractionDigits: 0 });
}

function fecha(iso, conHora = false) {
    if (!iso) return "—";

    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";

    const opciones = { day: "numeric", month: "short", year: "numeric" };
    if (conHora) {
        opciones.hour = "2-digit";
        opciones.minute = "2-digit";
    }

    return d.toLocaleDateString("es-CO", opciones);
}

function urlImagen(ruta) {
    if (!ruta) return null;
    return "/" + String(ruta).replace(/^\/+/, "").replace(/\\/g, "/");
}

const ICONOS = {
    carrito: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 5h4l3.2 15.2a2 2 0 0 0 2 1.6h11.6a2 2 0 0 0 2-1.5L28 11H8.4"/><circle cx="13" cy="27" r="1.8"/><circle cx="24" cy="27" r="1.8"/></svg>`,
    usuario: `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="16" cy="16" r="13"/><circle cx="16" cy="16" r="3.2" fill="currentColor"/></svg>`,
    buscar: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.6-4.6"/></svg>`,
    foto: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="10" width="36" height="28" rx="3"/><circle cx="17" cy="20" r="4"/><path d="M42 32l-10-10-16 16"/></svg>`,
    caja: `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l18-9 18 9v18l-18 9-18-9z"/><path d="M6 15l18 9 18-9M24 24v18"/></svg>`,
    rayo: `<svg viewBox="0 0 40 60" fill="currentColor" aria-hidden="true"><path d="M24 0L4 34h14l-4 26 22-36H22z"/></svg>`
};

const LOGO = `<svg viewBox="0 0 56 42" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M14 6h6l5 22h20l5-15H23"/>
    <circle cx="27" cy="36" r="3" fill="currentColor"/>
    <circle cx="42" cy="36" r="3" fill="currentColor"/>
    <path d="M2 14h12M5 20h11M8 26h9"/>
</svg>`;

function imagenProducto(ruta, alt) {
    const url = urlImagen(ruta);
    if (url) {
        return `<img src="${esc(url)}" alt="${esc(alt || "")}" loading="lazy">`;
    }
    return `<div class="sin-foto">${ICONOS.foto}</div>`;
}

/* Etiquetas de estados */

const ESTADOS = {
    // Pedidos
    PENDIENTE_PAGO: ["Pendiente de pago", "alerta"],
    PAGADO: ["Pagado", "proceso"],
    EN_PROCESO: ["En proceso", "proceso"],
    PARCIALMENTE_ENVIADO: ["Enviado parcialmente", "proceso"],
    COMPLETADO: ["Completado", "ok"],
    CANCELADO: ["Cancelado", "error"],
    // Pagos
    APROBADO: ["Aprobado", "ok"],
    RECHAZADO: ["Rechazado", "error"],
    // Ventas
    PENDIENTE: ["Pendiente", "alerta"],
    PREPARANDO: ["Preparando", "proceso"],
    ENVIADA: ["Enviada", "proceso"],
    ENTREGADA: ["Entregada", "ok"],
    CANCELACION_SOLICITADA: ["Cancelación solicitada", "alerta"],
    CANCELADA: ["Cancelada", "error"],
    // Envíos
    ENVIADO: ["Enviado", "proceso"],
    EN_TRANSITO: ["En tránsito", "proceso"],
    ENTREGADO: ["Entregado", "ok"],
    PROBLEMA: ["Con novedad", "alerta"],
    // Cancelaciones
    SOLICITADA: ["Solicitada", "alerta"],
    APROBADA: ["Aprobada", "ok"],
    RECHAZADA: ["Rechazada", "error"],
    // Productos
    PUBLICADO: ["Publicado", "ok"],
    PAUSADO: ["Pausado", "alerta"],
    AGOTADO: ["Agotado", "error"],
    ELIMINADO: ["Eliminado", "error"]
};

function textoEstado(estado) {
    return (ESTADOS[estado] || [estado])[0];
}

function etiquetaEstado(estado) {
    const [texto, tipo] = ESTADOS[estado] || [estado, ""];
    const clase = tipo ? ` estado-${tipo}` : "";
    return `<span class="estado${clase}">${esc(texto)}</span>`;
}

const CONDICIONES = {
    COMO_NUEVO: "Como nuevo",
    BUENO: "Buen estado",
    ACEPTABLE: "Aceptable"
};

const METODOS_PAGO = {
    SIMULADO: "Pago simulado",
    TARJETA_SIMULADA: "Tarjeta (simulada)",
    TRANSFERENCIA_SIMULADA: "Transferencia (simulada)"
};

/* ------------------------------------------------------------------ */
/* Avisos y ventanas modales                                           */
/* ------------------------------------------------------------------ */

function aviso(mensaje, tipo = "info") {
    let contenedor = document.querySelector(".avisos");

    if (!contenedor) {
        contenedor = document.createElement("div");
        contenedor.className = "avisos";
        contenedor.setAttribute("role", "status");
        document.body.appendChild(contenedor);
    }

    const elemento = document.createElement("div");
    elemento.className = `aviso aviso-${tipo}`;
    elemento.textContent = mensaje;
    contenedor.appendChild(elemento);

    setTimeout(() => elemento.remove(), tipo === "error" ? 6000 : 3500);
}

function abrirModal({ titulo, contenido, pie = "", chico = false }) {
    const fondo = document.createElement("div");
    fondo.className = "fondo-modal";
    fondo.innerHTML = `
        <div class="modal ${chico ? "modal-chico" : ""}" role="dialog" aria-modal="true">
            <div class="modal-cabecera">
                <h2>${esc(titulo)}</h2>
                <button type="button" class="cerrar-modal" aria-label="Cerrar">&times;</button>
            </div>
            <div class="modal-cuerpo">${contenido}</div>
            ${pie ? `<div class="modal-pie">${pie}</div>` : ""}
        </div>`;

    const cerrar = () => {
        fondo.remove();
        document.removeEventListener("keydown", alPresionar);
    };

    const alPresionar = (e) => {
        if (e.key === "Escape") cerrar();
    };

    fondo.querySelector(".cerrar-modal").addEventListener("click", cerrar);
    fondo.addEventListener("mousedown", (e) => {
        if (e.target === fondo) cerrar();
    });
    document.addEventListener("keydown", alPresionar);

    document.body.appendChild(fondo);

    return { elemento: fondo.querySelector(".modal"), cerrar };
}

function confirmar(mensaje, { titulo = "Confirmar", textoBoton = "Aceptar", peligro = false } = {}) {
    return new Promise((resolver) => {
        const { elemento, cerrar } = abrirModal({
            titulo,
            chico: true,
            contenido: `<p style="margin:0">${esc(mensaje)}</p>`,
            pie: `
                <button type="button" class="boton boton-secundario" data-r="no">Cancelar</button>
                <button type="button" class="boton ${peligro ? "boton-peligro" : ""}" data-r="si">${esc(textoBoton)}</button>`
        });

        let respondido = false;

        elemento.querySelectorAll("[data-r]").forEach((b) =>
            b.addEventListener("click", () => {
                respondido = true;
                cerrar();
                resolver(b.dataset.r === "si");
            })
        );

        // Si se cierra con la X o Escape
        const observador = new MutationObserver(() => {
            if (!document.body.contains(elemento)) {
                observador.disconnect();
                if (!respondido) resolver(false);
            }
        });
        observador.observe(document.body, { childList: true });
    });
}

function mostrarMensaje(contenedor, texto, tipo = "error", lista = null) {
    if (!contenedor) return;

    if (!texto) {
        contenedor.innerHTML = "";
        return;
    }

    const items = lista && lista.length
        ? `<ul>${lista.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`
        : "";

    contenedor.innerHTML = `<div class="mensaje mensaje-${tipo}">${esc(texto)}${items}</div>`;
}

async function conBoton(boton, tarea, textoProceso = "Procesando...") {
    const original = boton.innerHTML;
    boton.disabled = true;
    boton.textContent = textoProceso;

    try {
        return await tarea();
    } finally {
        boton.disabled = false;
        boton.innerHTML = original;
    }
}

/* ------------------------------------------------------------------ */
/* Encabezado y pie                                                    */
/* ------------------------------------------------------------------ */

function montarEncabezado({ busqueda = "" } = {}) {
    const destino = document.getElementById("encabezado");
    if (!destino) return;

    const usuario = Sesion.usuario();
    const activa = Sesion.activa() && usuario;

    destino.className = "encabezado";
    destino.innerHTML = `
        <div class="encabezado-contenido">
            <a class="logo" href="index.html" aria-label="Trama, ir al inicio">
                ${LOGO}
                <span class="logo-texto">
                    <span class="logo-nombre">Trama</span>
                    <span class="logo-lema">Tu mundo, en un solo clic</span>
                </span>
            </a>

            <form class="buscador" role="search" action="index.html">
                <input type="search" name="q" placeholder="Busca lo que más te gusta..."
                       value="${esc(busqueda)}" aria-label="Buscar productos">
                <button type="submit" aria-label="Buscar">${ICONOS.buscar}</button>
            </form>

            <nav class="menu-usuario">
                ${activa ? `
                    <a class="solo-escritorio" href="vender.html">Vender</a>
                    <a class="solo-escritorio" href="pedidos.html">Mis compras</a>
                ` : `
                    <a class="solo-escritorio" href="registro.html">Crea tu cuenta</a>
                    <a href="login.html">Ingresa</a>
                `}
                <a class="icono-carrito" href="carrito.html" aria-label="Carrito de compras">
                    ${ICONOS.carrito}
                    <span class="contador-carrito" id="contador-carrito">0</span>
                </a>
                <div class="cuenta">
                    <button type="button" class="boton-cuenta" id="boton-cuenta"
                            aria-haspopup="true" aria-expanded="false" aria-label="Mi cuenta">
                        ${ICONOS.usuario}
                    </button>
                    <div class="desplegable oculto" id="menu-cuenta">
                        ${activa ? `
                            <div class="saludo">Hola,<strong>${esc(usuario.nombre)} ${esc(usuario.apellido || "")}</strong></div>
                            <a href="perfil.html">Mi perfil</a>
                            <a href="pedidos.html">Mis compras</a>
                            <hr>
                            <a href="vender.html">Publicar artículo</a>
                            <a href="vender.html#mis-productos">Mis productos</a>
                            <a href="ventas.html">Mis ventas</a>
                            <hr>
                            <button type="button" id="cerrar-sesion">Cerrar sesión</button>
                        ` : `
                            <a href="login.html">Ingresar</a>
                            <a href="registro.html">Crear cuenta</a>
                        `}
                    </div>
                </div>
            </nav>
        </div>`;

    const boton = document.getElementById("boton-cuenta");
    const menu = document.getElementById("menu-cuenta");

    boton.addEventListener("click", (e) => {
        e.stopPropagation();
        const abierto = menu.classList.toggle("oculto") === false;
        boton.setAttribute("aria-expanded", String(abierto));
    });

    document.addEventListener("click", (e) => {
        if (!menu.contains(e.target)) {
            menu.classList.add("oculto");
            boton.setAttribute("aria-expanded", "false");
        }
    });

    const salir = document.getElementById("cerrar-sesion");
    if (salir) {
        salir.addEventListener("click", () => {
            Sesion.cerrar();
            window.location.href = "index.html";
        });
    }

    actualizarContadorCarrito();
}

async function actualizarContadorCarrito(cantidad) {
    const contador = document.getElementById("contador-carrito");
    if (!contador) return;

    if (typeof cantidad === "number") {
        contador.textContent = cantidad;
        return;
    }

    if (!Sesion.activa()) {
        contador.textContent = "0";
        return;
    }

    try {
        const carrito = await api("GET", "/carrito/");
        contador.textContent = (carrito.productos || []).reduce((s, p) => s + p.cantidad, 0);
    } catch (e) {
        contador.textContent = "0";
    }
}

function montarPie() {
    const destino = document.getElementById("pie");
    if (!destino) return;

    destino.className = "pie";
    destino.innerHTML = `
        <div class="pie-contenido">
            <span>© ${new Date().getFullYear()} Trama · Compra y vende tecnología usada</span>
            <span>Pagos simulados · <a href="/docs" target="_blank" rel="noopener">Documentación de la API</a></span>
        </div>`;
}

/* ------------------------------------------------------------------ */
/* Tarjeta de producto (inicio y búsqueda)                             */
/* ------------------------------------------------------------------ */

function tarjetaProducto(p) {
    const usuario = Sesion.usuario();
    const propio = usuario && usuario.id_usuario === p.id_vendedor;

    return `
        <article class="producto">
            <a class="foto" href="producto.html?id=${p.id_producto}">${imagenProducto(p.imagen_principal, p.nombre)}</a>
            <a class="nombre" href="producto.html?id=${p.id_producto}">${esc(p.nombre)}</a>
            <div class="precio">${precio(p.precio)}</div>
            <div class="detalle">${esc(CONDICIONES[p.condicion] || p.condicion)} · ${p.stock} disponible${p.stock === 1 ? "" : "s"}</div>
            ${propio
                ? `<a class="boton boton-secundario" href="vender.html#mis-productos">Es tu producto</a>`
                : `<button type="button" class="boton" data-agregar="${p.id_producto}">Agregar al carrito</button>`}
        </article>`;
}

async function agregarAlCarrito(idProducto, cantidad = 1) {
    if (!Sesion.activa()) {
        irAIngreso("Ingresa para agregar productos al carrito.");
        return false;
    }

    try {
        const r = await api("POST", "/carrito/agregar", {
            cuerpo: { id_producto: Number(idProducto), cantidad: Number(cantidad) }
        });
        aviso(`${r.nombre} agregado al carrito.`, "exito");
        actualizarContadorCarrito();
        return true;
    } catch (e) {
        aviso(e.message, "error");
        return false;
    }
}

/* Delegación: cualquier botón con data-agregar agrega una unidad */
document.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-agregar]");
    if (!boton) return;

    e.preventDefault();
    conBoton(boton, () => agregarAlCarrito(boton.dataset.agregar), "Agregando...");
});

/* Montaje automático */
document.addEventListener("DOMContentLoaded", () => {
    montarEncabezado({ busqueda: parametro("q") || "" });
    montarPie();
});
