// Prueba de interfaz (end-to-end): devolución de una compra entregada.
// Comprador solicita -> vendedor aprueba -> comprador registra el envío ->
// vendedor confirma la recepción -> reembolso.
// Requiere el backend en http://127.0.0.1:8000 con la base de datos lista.
//   node pruebas_e2e/recorrido_devoluciones.js
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

(async () => {
  const vend = await usuario('Camilo', 'Torres');
  const comp = await usuario('Sofia', 'Ramirez');

  const { id_producto } = await api('POST', '/productos/publicar', vend.token, {
    id_categoria: 1, nombre: 'Audífonos Sony WH-1000XM4', descripcion: 'Audífonos inalámbricos en buen estado, cancelación de ruido funcionando.',
    precio: 650000, stock: 3, condicion: 'BUENO', descripcion_defectos: 'Almohadillas con leve desgaste',
    checklist: { enciende: true, pantalla_sin_danos: true, bateria_ok: true } });
  for (const i of [1, 2, 3]) {
    const fd = new FormData(); fd.append('archivo', new Blob([fs.readFileSync(path.join(__dirname, 'fotos', `foto${i}.jpg`))], { type: 'image/jpeg' }), `foto${i}.jpg`);
    await fetch(`${B}/productos/${id_producto}/imagenes`, { method: 'POST', headers: { authorization: 'Bearer ' + vend.token }, body: fd });
  }
  const dir = await api('POST', '/direcciones/', comp.token, { direccion: 'Calle 80 # 15-30', ciudad: 'Bogotá', departamento: 'Cundinamarca' });
  await api('POST', '/carrito/agregar', comp.token, { id_producto, cantidad: 2 });
  const compra = await api('POST', '/pedidos/comprar', comp.token, { id_direccion: dir.id_direccion });
  const { id_envio } = await api('POST', `/envios/ventas/${compra.ventas[0].id_venta}`, vend.token, {});
  for (const estado of ['ENVIADO', 'EN_TRANSITO', 'ENTREGADO']) await api('PATCH', `/envios/${id_envio}/estado`, vend.token, { estado });

  const b = await chromium.launch();
  const page = await (await b.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 })).newPage();
  const errores = []; page.on('pageerror', (e) => errores.push(e.message));
  const sesion = (u) => page.evaluate(([t, us]) => { localStorage.setItem('ElectroMarket_token', t); localStorage.setItem('ElectroMarket_usuario', JSON.stringify(us)); localStorage.setItem('electromarket-tema', 'claro'); }, [u.token, u.usuario]);
  const foto = async (n, sel) => { await page.waitForTimeout(600); const el = sel ? page.locator(sel).last() : page; await el.screenshot({ path: `${out}/${n}.png`, ...(sel ? {} : { fullPage: true }) }); console.log('OK', n); };
  const enviarModal = async () => { await page.click('#enviar-dev'); await page.waitForSelector('#form-dev', { state: 'detached' }); await page.waitForTimeout(800); };

  // 1. El comprador solicita la devolución de 1 de las 2 unidades
  await page.goto(B + '/web/login.html'); await sesion(comp);
  await page.goto(`${B}/web/pedidos.html?pedido=${compra.id_pedido}`);
  await page.waitForSelector('.modal [data-devolver]'); await page.click('.modal [data-devolver]');
  await page.waitForSelector('#form-devolucion');
  await page.fill('.control-cantidad', '1');
  await page.selectOption('#motivo-dev', 'DEFECTUOSO');
  await page.fill('#descripcion-dev', 'El audífono izquierdo deja de sonar a los pocos minutos de uso.');
  await foto('devolucion-01-solicitar', '.modal');
  await page.click('#enviar-devolucion'); await page.waitForSelector('#form-devolucion', { state: 'detached' });
  await page.waitForSelector('.tarjeta-devolucion');
  await foto('devolucion-02-solicitada', '.tarjeta-devolucion');

  // 2. El vendedor la aprueba
  await sesion(vend); await page.goto(B + '/web/ventas.html');
  await page.waitForSelector('[data-dev-accion=aprobar]'); await page.click('[data-dev-accion=aprobar]');
  await page.fill('#observacion', 'Envíalos por Servientrega a la dirección de mi perfil.'); await enviarModal();

  // 3. El comprador registra el envío
  await sesion(comp); await page.goto(`${B}/web/pedidos.html?pedido=${compra.id_pedido}`);
  await page.waitForSelector('.modal [data-dev-accion=enviar]'); await page.click('.modal [data-dev-accion=enviar]');
  await page.fill('#transportadora', 'Servientrega'); await page.fill('#numero_guia', 'SV-2026-55821'); await enviarModal();

  // 4. El vendedor confirma la recepción y se genera el reembolso
  await sesion(vend); await page.goto(B + '/web/ventas.html');
  await page.waitForSelector('[data-dev-accion=recibir]'); await page.click('[data-dev-accion=recibir]');
  await page.waitForSelector('#form-dev'); await foto('devolucion-03-confirmar-recepcion', '.modal');
  await enviarModal();
  await page.click('#devoluciones-cerradas-bloque summary');
  await foto('devolucion-04-vendedor', '#devoluciones');

  // 5. El comprador ve el reembolso
  await sesion(comp); await page.goto(`${B}/web/pedidos.html?pedido=${compra.id_pedido}`);
  await page.waitForSelector('.estado-dev-recibida');
  await foto('devolucion-05-comprador', '.modal');
  const stock = (await api('GET', `/productos/${id_producto}`)).stock;
  if (stock !== 2) throw new Error(`Inventario esperado 2, obtenido ${stock}`);
  console.log('ERRORES JS:', errores.length ? errores : 'ninguno');
  await b.close();
})().catch((e) => { console.error('FALLO', e.message); process.exit(1); });
