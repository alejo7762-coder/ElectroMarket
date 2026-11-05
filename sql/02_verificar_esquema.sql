/* =====================================================================
   ElectroMarket - Verificación del esquema (solo lectura)
   ---------------------------------------------------------------------
   Comprueba que las restricciones CHECK de la base de datos acepten
   todos los estados que usa el código de las etapas 6 a 10.
   No modifica nada. Si aparece alguna fila en el resultado, ese valor
   debe agregarse a la restricción CHECK correspondiente.
   ===================================================================== */

SET NOCOUNT ON;

DECLARE @valores TABLE (
    Tabla   SYSNAME,
    Columna SYSNAME,
    Valor   VARCHAR(50)
);

INSERT INTO @valores (Tabla, Columna, Valor) VALUES
    -- Pedidos
    ('Pedidos', 'Estado', 'PENDIENTE_PAGO'),
    ('Pedidos', 'Estado', 'PAGADO'),
    ('Pedidos', 'Estado', 'EN_PROCESO'),
    ('Pedidos', 'Estado', 'PARCIALMENTE_ENVIADO'),
    ('Pedidos', 'Estado', 'COMPLETADO'),
    ('Pedidos', 'Estado', 'CANCELADO'),
    -- Ventas
    ('Ventas', 'Estado', 'PENDIENTE'),
    ('Ventas', 'Estado', 'PREPARANDO'),
    ('Ventas', 'Estado', 'ENVIADA'),
    ('Ventas', 'Estado', 'ENTREGADA'),
    ('Ventas', 'Estado', 'CANCELACION_SOLICITADA'),
    ('Ventas', 'Estado', 'CANCELADA'),
    -- Envios
    ('Envios', 'Estado', 'PREPARANDO'),
    ('Envios', 'Estado', 'ENVIADO'),
    ('Envios', 'Estado', 'EN_TRANSITO'),
    ('Envios', 'Estado', 'ENTREGADO'),
    ('Envios', 'Estado', 'PROBLEMA'),
    ('Envios', 'Estado', 'CANCELADO'),
    -- HistorialEnvios
    ('HistorialEnvios', 'Estado', 'CANCELADO'),
    -- Pagos
    ('Pagos', 'Estado', 'PENDIENTE'),
    ('Pagos', 'Estado', 'APROBADO'),
    ('Pagos', 'Estado', 'RECHAZADO'),
    ('Pagos', 'Metodo', 'SIMULADO'),
    ('Pagos', 'Metodo', 'TARJETA_SIMULADA'),
    ('Pagos', 'Metodo', 'TRANSFERENCIA_SIMULADA'),
    -- HistorialEstados
    ('HistorialEstados', 'TipoOperacion', 'PEDIDO'),
    ('HistorialEstados', 'TipoOperacion', 'VENTA'),
    -- Productos
    ('Productos', 'Estado', 'PUBLICADO'),
    ('Productos', 'Estado', 'PAUSADO'),
    ('Productos', 'Estado', 'AGOTADO'),
    ('Productos', 'Estado', 'ELIMINADO');

/* 1. Valores que alguna restricción CHECK de la columna NO acepta */
SELECT
    V.Tabla,
    V.Columna,
    V.Valor AS ValorNoPermitido,
    CC.name AS Restriccion,
    CC.definition AS DefinicionActual
FROM @valores V
INNER JOIN sys.check_constraints CC
    ON CC.parent_object_id = OBJECT_ID('dbo.' + V.Tabla)
   AND CC.definition LIKE '%\[' + V.Columna + '\]%' ESCAPE '\'
WHERE CC.definition NOT LIKE '%''' + V.Valor + '''%'
ORDER BY V.Tabla, V.Columna, V.Valor;

/* 2. Columnas que el código consulta y no existen */
DECLARE @columnas TABLE (Tabla SYSNAME, Columna SYSNAME);

INSERT INTO @columnas (Tabla, Columna) VALUES
    ('Direcciones', 'IdDireccion'), ('Direcciones', 'IdUsuario'),
    ('Direcciones', 'Direccion'), ('Direcciones', 'Ciudad'),
    ('Direcciones', 'Departamento'), ('Direcciones', 'CodigoPostal'),
    ('Pedidos', 'IdPedido'), ('Pedidos', 'IdComprador'),
    ('Pedidos', 'IdDireccion'), ('Pedidos', 'DireccionEntrega'),
    ('Pedidos', 'CiudadEntrega'), ('Pedidos', 'DepartamentoEntrega'),
    ('Pedidos', 'CodigoPostalEntrega'), ('Pedidos', 'Total'),
    ('Pedidos', 'Estado'),
    ('DetallesPedido', 'IdDetallePedido'), ('DetallesPedido', 'IdPedido'),
    ('DetallesPedido', 'IdProducto'), ('DetallesPedido', 'IdVendedor'),
    ('DetallesPedido', 'Cantidad'), ('DetallesPedido', 'PrecioUnitario'),
    ('DetallesPedido', 'Subtotal'),
    ('Pagos', 'IdPago'), ('Pagos', 'IdPedido'), ('Pagos', 'Valor'),
    ('Pagos', 'Metodo'), ('Pagos', 'Estado'), ('Pagos', 'Referencia'),
    ('Pagos', 'FechaPago'),
    ('Ventas', 'IdVenta'), ('Ventas', 'IdPedido'), ('Ventas', 'IdVendedor'),
    ('Ventas', 'Subtotal'), ('Ventas', 'Estado'),
    ('DetalleVenta', 'IdVenta'), ('DetalleVenta', 'IdDetallePedido'),
    ('Envios', 'IdEnvio'), ('Envios', 'IdVenta'), ('Envios', 'Estado'),
    ('Envios', 'FechaDespacho'), ('Envios', 'FechaEntrega'),
    ('HistorialEnvios', 'IdEnvio'), ('HistorialEnvios', 'Estado'),
    ('HistorialEnvios', 'Observacion'),
    ('HistorialEstados', 'TipoOperacion'), ('HistorialEstados', 'IdOperacion'),
    ('HistorialEstados', 'EstadoAnterior'), ('HistorialEstados', 'EstadoNuevo'),
    ('HistorialEstados', 'Observacion');

SELECT Tabla, Columna AS ColumnaInexistente
FROM @columnas
WHERE COL_LENGTH('dbo.' + Tabla, Columna) IS NULL;

/* 3. Columnas obligatorias de Direcciones sin valor por defecto
      (si aparece alguna distinta de las anteriores, avísame) */
SELECT C.name AS ColumnaObligatoria
FROM sys.columns C
WHERE C.object_id = OBJECT_ID('dbo.Direcciones')
  AND C.is_nullable = 0
  AND C.is_identity = 0
  AND C.default_object_id = 0
  AND C.name NOT IN ('IdUsuario', 'Direccion', 'Ciudad', 'Departamento', 'CodigoPostal');

PRINT 'Verificación terminada. Si las tres consultas salen vacías, el esquema es compatible.';

/* ---------------------------------------------------------------------
   Plantilla para corregir una restricción CHECK (ejemplo con Ventas).
   Reemplaza el nombre de la restricción por el que muestre la consulta 1
   y deja todos los valores que ya existían.

   ALTER TABLE dbo.Ventas DROP CONSTRAINT CK_Ventas_Estado;
   ALTER TABLE dbo.Ventas ADD CONSTRAINT CK_Ventas_Estado CHECK (
       Estado IN ('PENDIENTE', 'PREPARANDO', 'ENVIADA', 'ENTREGADA',
                  'CANCELACION_SOLICITADA', 'CANCELADA')
   );
   --------------------------------------------------------------------- */
