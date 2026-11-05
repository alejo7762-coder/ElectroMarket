/* =====================================================================
   ElectroMarket - Etapa 10: Cancelaciones parciales y totales
   ---------------------------------------------------------------------
   Crea las tablas que usa el módulo de cancelaciones:
     - Cancelaciones         (una por venta / vendedor afectado)
     - DetallesCancelacion   (qué productos y cuántas unidades)

   Es seguro ejecutarlo más de una vez: si una tabla ya existe no se
   vuelve a crear, y se informa si le falta alguna columna requerida.

   Ejecutar en SSMS sobre la base de datos de ElectroMarket.
   ===================================================================== */

SET NOCOUNT ON;
GO

/* ---------------------------------------------------------------------
   1. Tabla Cancelaciones
   --------------------------------------------------------------------- */
IF OBJECT_ID(N'dbo.Cancelaciones', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Cancelaciones (
        IdCancelacion          INT IDENTITY(1,1) NOT NULL,
        IdPedido               INT            NOT NULL,
        IdVenta                INT            NOT NULL,
        IdSolicitante          INT            NOT NULL,
        Tipo                   VARCHAR(10)    NOT NULL,
        Estado                 VARCHAR(15)    NOT NULL,
        Motivo                 NVARCHAR(500)  NOT NULL,
        MontoReembolso         DECIMAL(12,2)  NOT NULL
            CONSTRAINT DF_Cancelaciones_Monto DEFAULT (0),
        FechaSolicitud         DATETIME2(0)   NOT NULL
            CONSTRAINT DF_Cancelaciones_FechaSolicitud DEFAULT (SYSDATETIME()),
        FechaResolucion        DATETIME2(0)   NULL,
        IdResolutor            INT            NULL,
        ObservacionResolucion  NVARCHAR(500)  NULL,

        CONSTRAINT PK_Cancelaciones
            PRIMARY KEY (IdCancelacion),

        CONSTRAINT FK_Cancelaciones_Pedidos
            FOREIGN KEY (IdPedido) REFERENCES dbo.Pedidos (IdPedido),

        CONSTRAINT FK_Cancelaciones_Ventas
            FOREIGN KEY (IdVenta) REFERENCES dbo.Ventas (IdVenta),

        CONSTRAINT FK_Cancelaciones_Solicitante
            FOREIGN KEY (IdSolicitante) REFERENCES dbo.Usuarios (IdUsuario),

        CONSTRAINT FK_Cancelaciones_Resolutor
            FOREIGN KEY (IdResolutor) REFERENCES dbo.Usuarios (IdUsuario),

        -- TOTAL: cancela todas las unidades vigentes de la venta
        -- PARCIAL: cancela solo algunos productos o unidades
        CONSTRAINT CK_Cancelaciones_Tipo
            CHECK (Tipo IN ('TOTAL', 'PARCIAL')),

        -- SOLICITADA: espera respuesta del vendedor (venta ya despachada)
        -- APROBADA: aplicada (inventario devuelto y reembolso simulado)
        -- RECHAZADA: el vendedor no aceptó la solicitud
        CONSTRAINT CK_Cancelaciones_Estado
            CHECK (Estado IN ('SOLICITADA', 'APROBADA', 'RECHAZADA')),

        CONSTRAINT CK_Cancelaciones_Monto
            CHECK (MontoReembolso >= 0),

        CONSTRAINT CK_Cancelaciones_Resolucion
            CHECK (
                (Estado = 'SOLICITADA' AND FechaResolucion IS NULL)
                OR (Estado <> 'SOLICITADA' AND FechaResolucion IS NOT NULL)
            )
    );

    CREATE INDEX IX_Cancelaciones_Pedido ON dbo.Cancelaciones (IdPedido);
    CREATE INDEX IX_Cancelaciones_Venta  ON dbo.Cancelaciones (IdVenta, Estado);

    -- Solo puede existir una solicitud pendiente por venta
    CREATE UNIQUE INDEX UX_Cancelaciones_VentaSolicitada
        ON dbo.Cancelaciones (IdVenta)
        WHERE Estado = 'SOLICITADA';

    PRINT 'Tabla Cancelaciones creada.';
END
ELSE
    PRINT 'La tabla Cancelaciones ya existe: se verificarán sus columnas.';
GO

/* ---------------------------------------------------------------------
   2. Tabla DetallesCancelacion
   --------------------------------------------------------------------- */
IF OBJECT_ID(N'dbo.DetallesCancelacion', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.DetallesCancelacion (
        IdDetalleCancelacion  INT IDENTITY(1,1) NOT NULL,
        IdCancelacion         INT            NOT NULL,
        IdDetallePedido       INT            NOT NULL,
        Cantidad              INT            NOT NULL,
        Monto                 DECIMAL(12,2)  NOT NULL,

        CONSTRAINT PK_DetallesCancelacion
            PRIMARY KEY (IdDetalleCancelacion),

        CONSTRAINT FK_DetallesCancelacion_Cancelaciones
            FOREIGN KEY (IdCancelacion)
            REFERENCES dbo.Cancelaciones (IdCancelacion),

        CONSTRAINT FK_DetallesCancelacion_DetallesPedido
            FOREIGN KEY (IdDetallePedido)
            REFERENCES dbo.DetallesPedido (IdDetallePedido),

        CONSTRAINT UQ_DetallesCancelacion
            UNIQUE (IdCancelacion, IdDetallePedido),

        CONSTRAINT CK_DetallesCancelacion_Cantidad
            CHECK (Cantidad > 0),

        CONSTRAINT CK_DetallesCancelacion_Monto
            CHECK (Monto >= 0)
    );

    CREATE INDEX IX_DetallesCancelacion_DetallePedido
        ON dbo.DetallesCancelacion (IdDetallePedido);

    PRINT 'Tabla DetallesCancelacion creada.';
END
ELSE
    PRINT 'La tabla DetallesCancelacion ya existe: se verificarán sus columnas.';
GO

/* ---------------------------------------------------------------------
   3. Verificación de columnas (por si las tablas ya existían)
   --------------------------------------------------------------------- */
DECLARE @requeridas TABLE (Tabla SYSNAME, Columna SYSNAME);

INSERT INTO @requeridas (Tabla, Columna) VALUES
    ('Cancelaciones', 'IdCancelacion'),
    ('Cancelaciones', 'IdPedido'),
    ('Cancelaciones', 'IdVenta'),
    ('Cancelaciones', 'IdSolicitante'),
    ('Cancelaciones', 'Tipo'),
    ('Cancelaciones', 'Estado'),
    ('Cancelaciones', 'Motivo'),
    ('Cancelaciones', 'MontoReembolso'),
    ('Cancelaciones', 'FechaSolicitud'),
    ('Cancelaciones', 'FechaResolucion'),
    ('Cancelaciones', 'IdResolutor'),
    ('Cancelaciones', 'ObservacionResolucion'),
    ('DetallesCancelacion', 'IdDetalleCancelacion'),
    ('DetallesCancelacion', 'IdCancelacion'),
    ('DetallesCancelacion', 'IdDetallePedido'),
    ('DetallesCancelacion', 'Cantidad'),
    ('DetallesCancelacion', 'Monto');

IF EXISTS (
    SELECT 1
    FROM @requeridas R
    WHERE COL_LENGTH('dbo.' + R.Tabla, R.Columna) IS NULL
)
BEGIN
    SELECT R.Tabla, R.Columna AS ColumnaFaltante
    FROM @requeridas R
    WHERE COL_LENGTH('dbo.' + R.Tabla, R.Columna) IS NULL;

    RAISERROR(
        'Faltan columnas en las tablas de cancelaciones (ver resultado). Ajusta la tabla o renómbrala y vuelve a ejecutar este script.',
        16, 1
    );
END
ELSE
    PRINT 'Estructura de cancelaciones verificada correctamente.';
GO
