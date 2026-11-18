/* =====================================================================
   ElectroMarket - Reseñas y calificaciones
   ---------------------------------------------------------------------
   Una reseña por producto en cada venta entregada: calificación del
   producto y del vendedor (1 a 5 estrellas) y un comentario opcional.
   Solo el comprador de la venta puede reseñar (lo valida el backend).
   Es seguro ejecutarlo más de una vez.
   ===================================================================== */

USE [ElectroMarket];
GO

SET NOCOUNT ON;
GO

IF OBJECT_ID(N'dbo.Resenas', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Resenas (
        IdResena              INT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Resenas PRIMARY KEY,
        IdVenta               INT            NOT NULL
            CONSTRAINT FK_Resenas_Ventas REFERENCES dbo.Ventas (IdVenta),
        IdProducto            INT            NOT NULL
            CONSTRAINT FK_Resenas_Productos REFERENCES dbo.Productos (IdProducto),
        IdComprador           INT            NOT NULL
            CONSTRAINT FK_Resenas_Comprador REFERENCES dbo.Usuarios (IdUsuario),
        IdVendedor            INT            NOT NULL
            CONSTRAINT FK_Resenas_Vendedor REFERENCES dbo.Usuarios (IdUsuario),
        CalificacionProducto  TINYINT        NOT NULL
            CONSTRAINT CK_Resenas_Producto CHECK (CalificacionProducto BETWEEN 1 AND 5),
        CalificacionVendedor  TINYINT        NOT NULL
            CONSTRAINT CK_Resenas_Vendedor CHECK (CalificacionVendedor BETWEEN 1 AND 5),
        Comentario            NVARCHAR(1000) NULL,
        FechaResena           DATETIME2(0)   NOT NULL
            CONSTRAINT DF_Resenas_Fecha DEFAULT (SYSDATETIME()),
        FechaEdicion          DATETIME2(0)   NULL,
        CONSTRAINT UQ_Resenas_Venta_Producto UNIQUE (IdVenta, IdProducto),
        CONSTRAINT CK_Resenas_Partes CHECK (IdComprador <> IdVendedor)
    );

    CREATE INDEX IX_Resenas_Producto ON dbo.Resenas (IdProducto);
    CREATE INDEX IX_Resenas_Vendedor ON dbo.Resenas (IdVendedor);
    PRINT 'Tabla Resenas creada.';
END
ELSE
    PRINT 'La tabla Resenas ya existe.';
GO
