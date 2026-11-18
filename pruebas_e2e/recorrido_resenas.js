// Prueba de interfaz (end-to-end): reseñas y fiabilidad del vendedor.
// Una compra entregada se califica desde «Mis compras»; luego se revisan la
// ficha del producto (vendedor, fiabilidad y reseñas) y el perfil del vendedor.
// Requiere el backend en http://127.0.0.1:8000 con la base de datos lista.
//   node pruebas_e2e/recorrido_resenas.js
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const B = process.env.ELECTROMARKET_URL || 'http://127.0.0.1:8000';
const out = process.argv[2] || path.join(__dirname, '..', 'docs', 'evidencias', 'capturas');
const sufijo = Date.now().toString(36);

async function api(metodo, ruta, token, cuerpo) {
  const r = await fetch(B + ruta, { method: metodo, headers: { 'content-type': 'application/json', ...(token ? { authorization: 'Bearer ' + token } : {}) }, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const j = await r.json(); if (!r.ok) throw new Error(ruta + ' ' + r.status + ' ' + JSON.stringify(j)); return j;
}
async function usuario(nombre, apellido) {
  const correo = `${nombre.toLowerCase()}.${sufijo}@demo.com`;
  await api('POST', '/usuarios/registro', null, { nombre, apellido, correo, contrasena: 'Demo12345' });
  const r = await api('POST', '/usuarios/login', null, { correo, contrasena: 'Demo12345' });
  return { token: r.access_token, usuario: r.usuario };
}
async function compraEntregada(comprador, vendedor, idProducto) {
  const dir = await api('POST', '/direcciones/', comprador.token, { direccion: 'Calle 10 # 5-20', ciudad: 'Bogotá', departamento: 'Cundinamarca' });
  await api('POST', '/carrito/agregar', comprador.token, { id_producto: idProducto, cantidad: 1 });
  const compra = await api('POST', '/pedidos/comprar', comprador.token, { id_direccion: dir.id_direccion });
  const idVenta = compra.ventas[0].id_venta;
  const { id_envio } = await api('POST', `/envios/ventas/${idVenta}`, vendedor.token, {});
  for (const estado of ['ENVIADO', 'EN_TRANSITO', 'ENTREGADO']) await api('PATCH', `/envios/${id_envio}/estado`, vendedor.token, { estado });
  return { idPedido: compra.id_pedido, idVenta };
}

(async () => {
  const vend = await usuario('Valentina', 'Rojas');
  const comp = await usuario('Luis', 'Pérez');
  const comp2 = await usuario('Andrea', 'Gómez');

  const { id_producto } = await api('POST', '/productos/publicar', vend.token, {
    id_categoria: 1, nombre: 'Samsung Galaxy S21 128 GB', descripcion: 'Celular en buen estado, funciona perfecto. Rayones leves en el marco.',
    precio: 1300000, stock: 5, condicion: 'BUENO', descripcion_defectos: 'Rayones leves en el marco',
    checklist: { enciende: true, pantalla_sin_danos: true, bateria_ok: true, accesorios_completos: true } });
  for (const i of [1, 2, 3]) {
    const fd = new FormData(); fd.append('archivo', new Blob([fs.readFileSync(path.join(__dirname, 'fotos', `foto${i}.jpg`))], { type: 'image/jpeg' }), `foto${i}.jpg`);
    const r = await fetch(`${B}/productos/${id_producto}/imagenes`, { method: 'POST', headers: { authorization: 'Bearer ' + vend.token }, body: fd });
    if (!r.ok) throw new Error('foto ' + r.status);
  }

  // Segunda compradora: reseña por la API (para mostrar la distribución)
  const c2 = await compraEntregada(comp2, vend, id_producto);
  await api('POST', '/resenas/', comp2.token, { id_venta: c2.idVenta, id_producto, calificacion_producto: 4, calificacion_vendedor: 5,
    comentario: 'Llegó en dos días, bien empacado. La batería dura un poco menos de lo esperado.' });

  const c1 = await compraEntregada(comp, vend, id_producto);

  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 })).newPage();
  const errores = []; page.on('pageerror', (e) => errores.push(e.message));
  const sesion = (u) => page.evaluate(([t, us]) => { localStorage.setItem('ElectroMarket_token', t); localStorage.setItem('ElectroMarket_usuario', JSON.stringify(us)); localStorage.setItem('electromarket-tema', 'claro'); }, [u.token, u.usuario]);
  const foto = async (n, sel) => { await page.waitForTimeout(600); const el = sel ? page.locator(sel).first() : page; await el.screenshot({ path: `${out}/${n}.png`, ...(sel ? {} : { fullPage: true }) }); console.log('OK', n); };

  // 1. El comprador califica desde Mis compras
  await page.goto(B + '/web/login.html'); await sesion(comp);
  await page.goto(`${B}/web/pedidos.html?pedido=${c1.idPedido}`);
  await page.waitForSelector('[data-resenar]');
  await page.click('[data-resenar]');
  await page.waitForSelector('#form-resena');
  await page.click('label[for=estrellas-producto-5]'); await page.click('label[for=estrellas-vendedor-5]');
  await page.fill('#comentario', 'Excelente estado, tal como se describía. La vendedora respondió rápido y el envío fue puntual.');
  await foto('resenas-01-calificar', '.modal-chico');
  await page.click('#enviar-resena');
  await page.waitForSelector('#form-resena', { state: 'detached' });
  await page.waitForSelector('.celda-resena .estrellas');
  await foto('resenas-02-pedido-calificado', '.modal');

  // 2. Cualquier visitante ve el vendedor y las reseñas en la ficha
  await page.goto(`${B}/web/producto.html?id=${id_producto}`);
  await page.waitForSelector('#vendedor-producto .fiabilidad'); await page.waitForSelector('#resenas-producto .resena');
  const total = await page.locator('#resenas-producto .resena').count();
  if (total !== 2) throw new Error(`Se esperaban 2 reseñas y hay ${total}`);
  await foto('resenas-03-ficha', '.producto-secundario');

  // 3. Perfil público del vendedor
  await page.click('#vendedor-producto a.boton'); await page.waitForSelector('#perfil .fiabilidad');
  await page.waitForSelector('#productos .producto');
  await foto('resenas-04-perfil-vendedor');

  // 4. Estrellas en el catálogo
  await page.goto(B + '/web/index.html'); await page.waitForSelector('.producto .resumen-estrellas');
  console.log('ERRORES JS:', errores.length ? errores : 'ninguno');
  await b.close();
})().catch((e) => { console.error('FALLO', e.message); process.exit(1); });
