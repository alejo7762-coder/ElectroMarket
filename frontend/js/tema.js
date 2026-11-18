/* Tema claro / oscuro. Se carga en <head> para evitar el parpadeo. */
(function () {
    var CLAVE = "electromarket-tema";
    var guardado = null;
    try { guardado = localStorage.getItem(CLAVE); } catch (e) { /* sin almacenamiento */ }
    var oscuro = guardado
        ? guardado === "oscuro"
        : window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.setAttribute("data-tema", oscuro ? "oscuro" : "claro");

    window.alternarTema = function () {
        var nuevo = document.documentElement.getAttribute("data-tema") === "oscuro" ? "claro" : "oscuro";
        document.documentElement.setAttribute("data-tema", nuevo);
        try { localStorage.setItem(CLAVE, nuevo); } catch (e) { /* sin almacenamiento */ }
        return nuevo;
    };
})();
