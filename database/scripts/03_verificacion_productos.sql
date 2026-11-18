/* =====================================================================
   ElectroMarket - Verificación del estado de los productos
   ---------------------------------------------------------------------
   Guarda el checklist que el vendedor completa al publicar y la
   descripción obligatoria de defectos. Con esto, el número de fotos y
   la condición, la tienda calcula la insignia VERIFICADO / PARCIAL /
   SIN_VERIFICAR. Es seguro ejecutarlo más de una vez.
   ===================================================================== */

SET NOCOUNT ON;
GO

IF OBJECT_ID(N'dbo.VerificacionProductos', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.VerificacionProductos (
        IdProducto           INT            NOT NULL
            CONSTRAINT PK_VerificacionProductos PRIMARY KEY
            CONSTRAINT FK_VerificacionProductos_Productos
            REFERENCES dbo.Productos (IdProducto),
        Enciende             BIT            NOT NULL,
        PantallaSinDanos     BIT            NOT NULL,
        BateriaOk            BIT            NOT NULL,
        SinReparaciones      BIT            NOT NULL
            CONSTRAINT DF_Verificacion_SinReparaciones DEFAULT (0),
        AccesoriosCompletos  BIT            NOT NULL
            CONSTRAINT DF_Verificacion_Accesorios DEFAULT (0),
        ConGarantia          BIT            NOT NULL
            CONSTRAINT DF_Verificacion_Garantia DEFAULT (0),
        DescripcionDefectos  NVARCHAR(1000) NOT NULL,
        FechaActualizacion   DATETIME2(0)   NOT NULL
            CONSTRAINT DF_Verificacion_Fecha DEFAULT (SYSDATETIME())
    );
    PRINT 'Tabla VerificacionProductos creada.';
END
ELSE
    PRINT 'La tabla VerificacionProductos ya existe.';
GO
