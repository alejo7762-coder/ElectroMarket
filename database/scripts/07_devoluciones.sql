/* =====================================================================
   ElectroMarket - Devoluciones después de la entrega
   ---------------------------------------------------------------------
   Flujo: SOLICITADA -> APROBADA -> ENVIADA -> RECIBIDA (o RECHAZADA).
   Al recibirse se registra un reembolso; por eso Reembolsos admite
   ahora una devolución en lugar de una solicitud de cancelación.
   Es seguro ejecutarlo más de una vez.
   ===================================================================== */

USE [ElectroMarket];
GO

SET NOCOUNT ON;
GO

IF OBJECT_ID(N'dbo.Devoluciones', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Devoluciones (
        IdDevolucion         INT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Devoluciones PRIMARY KEY,
        IdVenta              INT            NOT NULL
            CONSTRAINT FK_Devoluciones_Ventas REFERENCES dbo.Ventas (IdVenta),
        IdPedido             INT            NOT NULL
            CONSTRAINT FK_Devoluciones_Pedidos REFERENCES dbo.Pedidos (IdPedido),
        IdComprador          INT            NOT NULL
            CONSTRAINT FK_Devoluciones_Comprador REFERENCES dbo.Usuarios (IdUsuario),
        IdVendedor           INT            NOT NULL
            CONSTRAINT FK_Devoluciones_Vendedor REFERENCES dbo.Usuarios (IdUsuario),
        Motivo               VARCHAR(30)    NOT NULL
            CONSTRAINT CK_Devoluciones_Motivo CHECK (Motivo IN (
                'DEFECTUOSO', 'NO_COINCIDE', 'LLEGO_DANADO', 'EQUIVOCADO', 'ARREPENTIMIENTO')),
        Descripcion          NVARCHAR(1000) NOT NULL,
        Estado               VARCHAR(15)    NOT NULL
            CONSTRAINT DF_Devoluciones_Estado DEFAULT ('SOLICITADA')
            CONSTRAINT CK_Devoluciones_Estado CHECK (Estado IN (
                'SOLICITADA', 'APROBADA', 'RECHAZADA', 'ENVIADA', 'RECIBIDA')),
        MontoReembolso       DECIMAL(12,2)  NOT NULL
            CONSTRAINT CK_Devoluciones_Monto CHECK (MontoReembolso > 0),
        ObservacionVendedor  NVARCHAR(500)  NULL,
        Transportadora       VARCHAR(100)   NULL,
        NumeroGuia           VARCHAR(100)   NULL,
        ReintegradoInventario BIT           NULL,
        FechaSolicitud       DATETIME2(0)   NOT NULL
            CONSTRAINT DF_Devoluciones_Fecha DEFAULT (SYSDATETIME()),
        FechaRespuesta       DATETIME2(0)   NULL,
        FechaEnvio           DATETIME2(0)   NULL,
        FechaRecepcion       DATETIME2(0)   NULL
    );
    CREATE INDEX IX_Devoluciones_Venta ON dbo.Devoluciones (IdVenta);
    PRINT 'Tabla Devoluciones creada.';
END
GO

IF OBJECT_ID(N'dbo.DetalleDevolucion', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.DetalleDevolucion (
        IdDetalleDevolucion  INT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_DetalleDevolucion PRIMARY KEY,
        IdDevolucion         INT NOT NULL
            CONSTRAINT FK_DetalleDevolucion_Devolucion REFERENCES dbo.Devoluciones (IdDevolucion),
        IdDetallePedido      INT NOT NULL
            CONSTRAINT FK_DetalleDevolucion_DetallePedido REFERENCES dbo.DetallesPedido (IdDetallePedido),
        Cantidad             INT NOT NULL
            CONSTRAINT CK_DetalleDevolucion_Cantidad CHECK (Cantidad > 0),
        CONSTRAINT UQ_DetalleDevolucion UNIQUE (IdDevolucion, IdDetallePedido)
    );
    PRINT 'Tabla DetalleDevolucion creada.';
END
GO

/* Reembolsos: origen en una cancelación o en una devolución (exactamente uno) */
IF COL_LENGTH('dbo.Reembolsos', 'IdDevolucion') IS NULL
BEGIN
    ALTER TABLE dbo.Reembolsos ADD IdDevolucion INT NULL
        CONSTRAINT FK_Reembolsos_Devoluciones REFERENCES dbo.Devoluciones (IdDevolucion);
    PRINT 'Columna Reembolsos.IdDevolucion agregada.';
END
GO

IF EXISTS (SELECT 1 FROM sys.columns
           WHERE object_id = OBJECT_ID('dbo.Reembolsos') AND name = 'IdSolicitud' AND is_nullable = 0)
BEGIN
    ALTER TABLE dbo.Reembolsos ALTER COLUMN IdSolicitud INT NULL;
    PRINT 'Reembolsos.IdSolicitud ahora admite NULL.';
END
GO

IF OBJECT_ID(N'dbo.CK_Reembolsos_Origen', N'C') IS NULL
    ALTER TABLE dbo.Reembolsos ADD CONSTRAINT CK_Reembolsos_Origen CHECK (
        (IdSolicitud IS NOT NULL AND IdDevolucion IS NULL) OR (IdSolicitud IS NULL AND IdDevolucion IS NOT NULL));
GO

PRINT 'Devoluciones listas.';
GO
