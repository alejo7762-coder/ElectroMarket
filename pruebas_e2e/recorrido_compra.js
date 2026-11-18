// Prueba de interfaz (end-to-end): recorrido de compra, cancelación y reembolso.
// Requiere el backend en http://127.0.0.1:8000 con la base de datos lista.
// Uso (desde la raíz del repositorio):
//   npm install playwright && npx playwright install chromium
//   node pruebas_e2e/recorrido_compra.js
const { chromium } = require('playwright');
const B = process.env.ELECTROMARKET_URL || 'http://127.0.0.1:8000';
const path = require('path');
const out = process.argv[2] || path.join(__dirname, '..', 'docs', 'evidencias', 'capturas');
const sufijo = Date.now().toString(36);
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

async function api(metodo, ruta, token, cuerpo) {
  const r = await fetch(B + ruta, { method: metodo, headers: { 'content-type': 'application/json', ...(token ? { authorization: 'Bearer ' + token } : {}) }, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const j = await r.json(); if (!r.ok) throw new Error(ruta + ' ' + r.status + ' ' + JSON.stringify(j)); return j;
}

(async () => {
  // Vendedor y producto con 3 fotos (por API)
  const vend = { nombre: 'Ana', apellido: 'Vendedora', correo: `ana.${sufijo}@demo.com`, contrasena: 'Demo12345' };
  await api('POST', '/usuarios/registro', null, vend);
  const tv = (await api('POST', '/usuarios/login', null, { correo: vend.correo, contrasena: vend.contrasena })).access_token;
  const { id_producto } = await api('POST', '/productos/publicar', tv, {
    id_categoria: 1, nombre: 'iPhone 12 128GB demo ' + sufijo, descripcion: 'Usado, funciona perfecto.', precio: 1850000, stock: 3, condicion: 'BUENO',
    checklist: { enciende: true, pantalla_sin_danos: true, bateria_ok: true, accesorios_completos: true }, descripcion_defectos: 'Rayón leve en la esquina superior.' });
  for (let i = 0; i < 3; i++) {
    const fd = new FormData(); fd.append('archivo', new Blob([png], { type: 'image/png' }), `f${i}.png`);
    const r = await fetch(`${B}/productos/${id_producto}/imagenes`, { method: 'POST', headers: { authorization: 'Bearer ' + tv }, body: fd });
    if (!r.ok) throw new Error('foto ' + r.status + await r.text());
  }

  const b = await chromium.launch(); const page = await (await b.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
  await page.addInitScript(() => localStorage.setItem('electromarket-tema', 'claro'));
  const errores = []; page.on('pageerror', e => errores.push(e.message));
  const paso = async (n) => { await page.waitForTimeout(600); await page.screenshot({ path: `${out}/compra-${n}.png`, fullPage: true }); console.log('OK', n); };

  // 1. Registro del comprador por la interfaz
  await page.goto(B + '/web/registro.html');
  await page.fill('[name=nombre]', 'Luis'); await page.fill('[name=apellido]', 'Comprador');
  await page.fill('[name=correo]', `luis.${sufijo}@demo.com`); await page.fill('[name=contrasena]', 'Demo12345');
  await page.selectOption('[name=dia]', '2'); await page.selectOption('[name=mes]', '4'); await page.selectOption('[name=anio]', '1995');
  await page.selectOption('[name=genero]', 'OTRO'); await page.click('#boton-registro'); await page.waitForURL(/index|login|web\/$/, { timeout: 8000 }).catch(() => {});
  if (page.url().includes('login')) { await page.fill('#correo', `luis.${sufijo}@demo.com`); await page.fill('#contrasena', 'Demo12345'); await page.click('#boton-ingreso'); await page.waitForURL(/index|web\/$/); }
  await paso('01-inicio-con-sesion');

  // 2. Ficha del producto con verificación y agregar al carrito
  await page.goto(`${B}/web/producto.html?id=${id_producto}`); await paso('02-producto-verificado');
  await page.click('#agregar'); await page.waitForTimeout(800);

  // 3. Carrito -> checkout con dirección nueva
  await page.goto(B + '/web/carrito.html'); await paso('03-carrito');
  const tc = await page.evaluate(() => localStorage.getItem('ElectroMarket_token'));
  await api('POST', '/direcciones/', tc, { direccion: 'Calle 10 # 5-20', ciudad: 'Bogotá', departamento: 'Cundinamarca', codigo_postal: '110111' });
  await page.goto(B + '/web/checkout.html'); await page.waitForSelector('#confirmar'); await paso('04-checkout');
  await page.click('#confirmar'); await page.waitForURL(/pedidos/, { timeout: 8000 }).catch(() => {}); await paso('05-compra-confirmada');

  // 4. Mis compras: cancelar el pedido
  await page.goto(B + '/web/pedidos.html'); await page.click('[data-ver]'); await page.waitForSelector('#cancelar-total');
  await page.click('#cancelar-total'); await page.fill('#motivo', 'Ya no necesito el producto'); await page.click('#form-motivo button[type=submit]');
  await page.waitForTimeout(1500); await paso('06-pedido-cancelado');
  await page.keyboard.press('Escape'); await page.goto(B + '/web/pedidos.html'); await paso('07-reembolso-en-proceso');

  // 5. Vendedor: Mis ventas
  await page.evaluate(([t]) => { localStorage.setItem('ElectroMarket_token', t); localStorage.setItem('ElectroMarket_usuario', JSON.stringify({ id_usuario: 0, nombre: 'Ana', apellido: 'Vendedora' })); }, [tv]);
  await page.goto(B + '/web/ventas.html'); await paso('08-mis-ventas');

  console.log('ERRORES JS:', errores.length ? errores : 'ninguno');
  await b.close();
})().catch(e => { console.error('FALLO', e.message); process.exit(1); });

