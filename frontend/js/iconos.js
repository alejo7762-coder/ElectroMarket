"use strict";

/* =====================================================================
   ElectroMarket - Iconos
   ---------------------------------------------------------------------
   Set propio de iconos de línea (SVG en el código, sin dependencias ni
   conexión a internet). Todos usan una cuadrícula de 24x24 y toman el
   color del texto (currentColor).

   - icono(nombre, clase): devuelve el SVG para usarlo en plantillas.
   - data-icono="nombre": en el HTML agrega el icono al inicio del elemento.
   - Los botones y enlaces del menú reciben su icono según el texto
     (ICONO_POR_TEXTO), también los que se crean después con JavaScript.
   ===================================================================== */

const TRAZOS = {
    usuario: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    cuenta: '<circle cx="12" cy="12" r="9.5"/><circle cx="12" cy="10" r="3.2"/><path d="M6.3 18.4c1.3-2 3.3-3.2 5.7-3.2s4.4 1.2 5.7 3.2"/>',
    usuarioMas: '<circle cx="10" cy="8" r="4"/><path d="M3 21c0-4 3.1-7 7-7 1.5 0 2.9.4 4 1.2M19 14v6M16 17h6"/>',
    carrito: '<path d="M3 4h2.5l2.4 11.2a1.6 1.6 0 0 0 1.6 1.3h8.3a1.6 1.6 0 0 0 1.6-1.2L21 8H6.3"/><circle cx="10" cy="20.5" r="1.3"/><circle cx="18" cy="20.5" r="1.3"/>',
    carritoMas: '<path d="M3 4h2.5l2.4 11.2a1.6 1.6 0 0 0 1.6 1.3h8.3a1.6 1.6 0 0 0 1.6-1.2L21 8H6.3M12 10.5h5M14.5 8v5"/><circle cx="10" cy="20.5" r="1.3"/><circle cx="18" cy="20.5" r="1.3"/>',
    bolsa: '<path d="M5 8h14l-1 12.2a1.5 1.5 0 0 1-1.5 1.3h-9A1.5 1.5 0 0 1 6 20.2zM9 8V6.5a3 3 0 0 1 6 0V8"/>',
    etiqueta: '<path d="M3 11.8V4.5A1.5 1.5 0 0 1 4.5 3h7.3a1.5 1.5 0 0 1 1.1.4l7.7 7.7a1.5 1.5 0 0 1 0 2.1l-7.3 7.3a1.5 1.5 0 0 1-2.1 0l-7.7-7.7a1.5 1.5 0 0 1-.4-1z"/><circle cx="8" cy="8" r="1.5"/>',
    inventario: '<path d="M3.5 7.5L12 3l8.5 4.5v9L12 21l-8.5-4.5zM3.5 7.5L12 12l8.5-4.5M12 12v9"/>',
    grafico: '<path d="M3 20h18M6 20v-6M11 20V9M16 20v-9M21 4l-5 4-4-3-5 4"/>',
    tienda: '<path d="M4 9.5L5.5 4h13L20 9.5M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0M5 12v8h14v-8M10 20v-5h4v5"/>',
    ingresar: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l4-4-4-4M14 12H4"/>',
    salir: '<path d="M9 20H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h3M16 16l4-4-4-4M20 12H10"/>',
    buscar: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
    sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6L6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4"/>',
    luna: '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z"/>',
    mas: '<path d="M12 5v14M5 12h14"/>',
    menos: '<path d="M5 12h14"/>',
    basura: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12.5A1.5 1.5 0 0 0 8.5 21h7a1.5 1.5 0 0 0 1.5-1.5L18 7M9 7V4.5A1.5 1.5 0 0 1 10.5 3h3A1.5 1.5 0 0 1 15 4.5V7"/>',
    editar: '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16zM13.5 6.5l4 4"/>',
    pausa: '<rect x="6.5" y="5" width="3.5" height="14" rx="1"/><rect x="14" y="5" width="3.5" height="14" rx="1"/>',
    reanudar: '<path d="M7.5 5.2v13.6a1 1 0 0 0 1.5.9l10.6-6.8a1 1 0 0 0 0-1.7L9 4.3a1 1 0 0 0-1.5.9z"/>',
    camion: '<path d="M2.5 6.5h11v9.5h-11zM13.5 9.5h4l3.5 3.5v3h-7.5"/><circle cx="6.5" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    tarjeta: '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19M6.5 15h4"/>',
    banco: '<path d="M3 9.5L12 4l9 5.5M5 10v7.5M9.7 10v7.5M14.3 10v7.5M19 10v7.5M3 20.5h18"/>',
    billetera: '<path d="M19 8V6a1.5 1.5 0 0 0-1.5-1.5h-12A2.5 2.5 0 0 0 3 7v11a2 2 0 0 0 2 2h14.5a1.5 1.5 0 0 0 1.5-1.5V9.5A1.5 1.5 0 0 0 19.5 8H5.5A2.5 2.5 0 0 1 3 5.5"/><circle cx="16.5" cy="14" r="1.2"/>',
    ubicacion: '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    escudoCheck: '<path d="M12 3l7.5 3v5.5c0 4.7-3.2 8.3-7.5 9.5-4.3-1.2-7.5-4.8-7.5-9.5V6zM8.8 12l2.2 2.2 4.4-4.4"/>',
    escudoMedio: '<path d="M12 3l7.5 3v5.5c0 4.7-3.2 8.3-7.5 9.5-4.3-1.2-7.5-4.8-7.5-9.5V6zM12 3v18"/>',
    escudoPregunta: '<path d="M12 3l7.5 3v5.5c0 4.7-3.2 8.3-7.5 9.5-4.3-1.2-7.5-4.8-7.5-9.5V6zM10 9.8a2 2 0 1 1 2.8 1.8c-.5.2-.8.7-.8 1.2v.4M12 16h.01"/>',
    reembolso: '<path d="M3.5 12a8.5 8.5 0 1 0 2.5-6M3.5 3.5V8H8M14.5 9.5h-3.2a1.4 1.4 0 0 0 0 2.8h1.4a1.4 1.4 0 0 1 0 2.8H9.5M12 8v1.5M12 15.1v1.4"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    cerrar: '<path d="M6 6l12 12M18 6L6 18"/>',
    alerta: '<path d="M10.3 4.3L2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="9.5"/><path d="M12 11v5.5M12 7.5h.01"/>',
    historial: '<path d="M3.5 12a8.5 8.5 0 1 0 2.5-6M3.5 3.5V8H8M12 7.5V12l3 2"/>',
    ojo: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    candado: '<rect x="4.5" y="10.5" width="15" height="10.5" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3M12 14.5v2.5"/>',
    correo: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5l8.5 6.5 8.5-6.5"/>',
    guardar: '<path d="M6 3h10l4 4v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM8 3v5h7V3M7.5 21v-7h9v7"/>',
    volver: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    izquierda: '<path d="M15 18l-6-6 6-6"/>',
    derecha: '<path d="M9 18l6-6-6-6"/>',
    mensaje: '<path d="M4 5.5h16v11H9.5L4 20.5z"/>',
    enviar: '<path d="M21 3L10 14M21 3l-6.5 18-4.5-9-9-4.5z"/>',
    estrella: '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.8l-5.2 2.8 1-5.8-4.3-4.1 5.9-.8z"/>',
    relampago: '<path d="M13 2.5L4.5 13.5H11l-1 8 8.5-11H12z"/>',
    camara: '<path d="M4 8h3l1.5-2.5h7L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13.5" r="3.5"/>',
    calendario: '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    foto: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="10" r="2"/><path d="M21 16l-5-5-8 8"/>',
    ia: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 15.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8zM5.5 2.5l.6 1.5 1.5.6-1.5.6-.6 1.5-.6-1.5L3.4 4.6l1.5-.6z"/>',
    caja: '<path d="M3.5 7.5L12 3l8.5 4.5v9L12 21l-8.5-4.5zM3.5 7.5L12 12l8.5-4.5M12 12v9"/>'
};

function icono(nombre, clase = "") {
    const trazo = TRAZOS[nombre];
    if (!trazo) return "";
    return `<svg class="icono${clase ? " " + clase : ""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${trazo}</svg>`;
}

/* Iconos usados por api.js y las páginas */
const ICONOS = {
    carrito: icono("carrito"),
    usuario: icono("cuenta"),
    buscar: icono("buscar"),
    foto: icono("foto"),
    ia: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 15.5l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8zM5.5 2.5l.6 1.5 1.5.6-1.5.6-.6 1.5-.6-1.5L3.4 4.6l1.5-.6z"/>',
    caja: icono("caja"),
    rayo: `<svg viewBox="0 0 40 60" fill="currentColor" aria-hidden="true"><path d="M24 0L4 34h14l-4 26 22-36H22z"/></svg>`
};

/* Texto del botón (o enlace del menú) -> icono */
const ICONO_POR_TEXTO = [
    // exactos
    ["Analizar con IA", "ia"], ["Usar condición sugerida", "check"],
    ["Agregar al carrito", "carritoMas"], ["Comprar ahora", "relampago"],
    ["Ir a la tienda", "tienda"], ["Seguir comprando", "tienda"], ["Volver a la tienda", "tienda"],
    ["Eliminar", "basura"], ["Quitar", "basura"], ["Vaciar carrito", "basura"],
    ["Editar", "editar"], ["Editar publicación", "editar"], ["Gestionar", "editar"],
    ["Pausar", "pausa"], ["Reactivar", "reanudar"], ["Hacer principal", "estrella"],
    ["Ver detalle", "ojo"], ["Ver mi pedido", "bolsa"], ["Seguimiento", "camion"], ["Crear envío", "camion"],
    ["Ver historial", "historial"], ["Ver historial de estados", "historial"],
    ["Responder", "mensaje"], ["Aprobar", "check"], ["Rechazar", "cerrar"], ["Enviar solicitud", "enviar"],
    ["Guardar cambios", "guardar"], ["Guardar dirección", "guardar"], ["Cambiar contraseña", "candado"],
    ["Agregar dirección", "mas"], ["Publicar artículo", "etiqueta"], ["Es tu producto", "etiqueta"],
    ["Ingresar", "ingresar"], ["Ingresa", "ingresar"], ["Crear cuenta", "usuarioMas"], ["Crea tu cuenta", "usuarioMas"],
    ["Cerrar sesión", "salir"], ["Mi perfil", "usuario"], ["Mis compras", "bolsa"], ["Vender", "etiqueta"],
    ["Mis productos", "inventario"], ["Mis ventas", "grafico"],
    ["Datos personales", "usuario"], ["Contraseña", "candado"], ["Direcciones", "ubicacion"],
    ["Volver", "volver"], ["Volver al carrito", "volver"],
    // por prefijo (terminan en *)
    ["Pagar*", "candado"], ["Continuar compra*", "tarjeta"], ["Solicitar cancelación*", "alerta"],
    ["Cancelar*", "cerrar"], ["Guardar*", "guardar"], ["Publicar*", "etiqueta"]
];

const SELECTOR_DECORABLE = ".boton, .boton-texto, .desplegable a, .desplegable button, .menu-usuario > a, .pestanas button, .enlace-pie";

function iconoParaTexto(texto) {
    for (const [patron, nombre] of ICONO_POR_TEXTO) {
        if (patron.endsWith("*") ? texto.startsWith(patron.slice(0, -1)) : texto === patron) {
            return nombre;
        }
    }
    return null;
}

function decorarElemento(el) {
    if (el.dataset.iconoListo || el.querySelector("svg") || el.hasAttribute("data-sin-icono")) return;

    const texto = el.textContent.trim().replace(/^\+\s*/, "");
    const nombre = el.dataset.icono || iconoParaTexto(texto);
    el.dataset.iconoListo = "1";
    if (!nombre) return;

    el.insertAdjacentHTML("afterbegin", icono(nombre));
}

function decorar(raiz) {
    if (!(raiz instanceof Element)) return;

    // Botones de cantidad (+ y −) pasan a ser iconos
    raiz.querySelectorAll(".selector-cantidad button").forEach((b) => {
        const t = b.textContent.trim();
        if (t === "+" || t === "−") b.innerHTML = icono(t === "+" ? "mas" : "menos");
    });

    if (raiz.matches(SELECTOR_DECORABLE) || raiz.matches("[data-icono]")) decorarElemento(raiz);
    raiz.querySelectorAll(SELECTOR_DECORABLE + ", [data-icono]").forEach(decorarElemento);
}

document.addEventListener("DOMContentLoaded", () => {
    decorar(document.body);

    // También el contenido que las páginas crean después
    new MutationObserver((cambios) => {
        for (const cambio of cambios) cambio.addedNodes.forEach(decorar);
    }).observe(document.body, { childList: true, subtree: true });
});
