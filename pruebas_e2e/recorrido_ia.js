// Prueba de interfaz (end-to-end) del servicio de IA: analizar, corregir y publicar.
// Requiere el backend en http://127.0.0.1:8000 con la base de datos lista.
// Uso (desde la raíz del repositorio):
//   npm install playwright && npx playwright install chromium
//   node pruebas_e2e/recorrido_ia.js
const { chromium } = require('playwright');
const B = process.env.ELECTROMARKET_URL || 'http://127.0.0.1:8000';
const path = require('path');
const out = process.argv[2] || path.join(__dirname, '..', 'docs', 'evidencias', 'capturas');
const fotos = path.join(__dirname, 'fotos');
const sufijo = Date.now().toString(36);

async function api(metodo, ruta, token, cuerpo) {
  const r = await fetch(B + ruta, { method: metodo, headers: { 'content-type': 'application/json', ...(token ? { authorization: 'Bearer ' + token } : {}) }, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const j = await r.json(); if (!r.ok) throw new Error(ruta + ' ' + r.status + ' ' + JSON.stringify(j)); return j;
}
async function usuario(nombre) {
  const correo = `${nombre.toLowerCase()}.${sufijo}@demo.com`;
  await api('POST', '/usuarios/registro', null, { nombre, apellido: 'Demo', correo, contrasena: 'Demo12345' });
  const r = await api('POST', '/usuarios/login', null, { correo, contrasena: 'Demo12345' });
  return { token: r.access_token, usuario: r.usuario };
}

(async () => {
  const vend = await usuario('Ana'); const comp = await usuario('Luis');
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage(); const errores = []; page.on('pageerror', e => errores.push(e.message));
  const sesion = async (u) => page.evaluate(([t, us]) => { localStorage.setItem('ElectroMarket_token', t); localStorage.setItem('ElectroMarket_usuario', JSON.stringify(us)); localStorage.setItem('electromarket-tema', 'claro'); }, [u.token, u.usuario]);
  const foto = async (n, sel) => { await page.waitForTimeout(500); const el = sel ? page.locator(sel) : page; await el.screenshot({ path: `${out}/${n}.png`, ...(sel ? {} : { fullPage: true }) }); console.log('OK', n); };

  // 1. Vendedor redacta una publicación incoherente y la analiza con IA
  await page.goto(B + '/web/login.html'); await sesion(vend);
  await page.goto(B + '/web/vender.html'); await page.waitForSelector('#id_categoria option[value="1"]', { state: 'attached' });
  await page.fill('[name=nombre]', 'iPhone 11 de 64 GB'); await page.selectOption('[name=id_categoria]', '1');
  await page.fill('[name=descripcion]', 'iPhone 11 como nuevo. La pantalla está rota en una esquina y la batería dura poco, pero funciona.');
  await page.fill('[name=precio]', '900000'); await page.selectOption('[name=condicion]', 'COMO_NUEVO');
  for (const c of ['enciende', 'pantalla_sin_danos', 'bateria_ok']) await page.check(`[name=${c}]`);
  await page.fill('[name=descripcion_defectos]', 'Ninguno');
  await page.click('#analizar-ia'); await page.waitForSelector('.panel-ia');
  await foto('ia-01-analisis-incoherente', '.checklist-estado');

  // 2. Usa la condición sugerida, corrige el checklist y vuelve a analizar
  await page.click('[data-usar-condicion]');
  await page.uncheck('[name=pantalla_sin_danos]'); await page.uncheck('[name=bateria_ok]');
  await page.fill('[name=descripcion]', 'iPhone 11 funcionando. La pantalla está rota en una esquina y la batería dura poco.');
  await page.fill('[name=descripcion_defectos]', 'Pantalla rota en una esquina, batería deteriorada');
  await page.click('#analizar-ia'); await page.waitForTimeout(800);
  await foto('ia-02-analisis-coherente', '.checklist-estado');

  // 3. Publica con 3 fotos
  await page.setInputFiles('#fotos', [1, 2, 3].map(i => `${fotos}/foto${i}.jpg`));
  await page.click('#boton-guardar'); await page.waitForTimeout(2500);
  const mis = await api('GET', '/mis-productos/', vend.token);
  const id = mis.productos[0].id_producto;

  // 4. Publicación incoherente (para mostrar la alerta en Mis productos y al comprador)
  const id2 = (await api('POST', '/productos/publicar', vend.token, {
    id_categoria: 1, nombre: 'Portátil Lenovo IdeaPad', descripcion: 'Portátil como nuevo, se recalienta y se apaga solo cuando lo exijo.',
    precio: 1200000, stock: 1, condicion: 'COMO_NUEVO', checklist: { enciende: true, pantalla_sin_danos: true, bateria_ok: true }, descripcion_defectos: 'Ninguno' })).id_producto;
  await page.goto(B + '/web/index.html'); await page.goto(B + '/web/vender.html#mis-productos'); await page.waitForSelector('#tabla-productos table');
  await foto('ia-03-mis-productos', '#tabla-productos');

  // 5. El comprador ve el análisis en la ficha
  await sesion(comp);
  await page.goto(`${B}/web/producto.html?id=${id}`); await page.waitForSelector('.panel-ia');
  await foto('ia-04-ficha-coherente');
  await page.goto(`${B}/web/producto.html?id=${id2}`); await page.waitForSelector('.panel-ia');
  await foto('ia-05-ficha-revisar', '.panel-verificacion');

  console.log('ERRORES JS:', errores.length ? errores : 'ninguno');
  await b.close();
})().catch(e => { console.error('FALLO', e.message); process.exit(1); });
