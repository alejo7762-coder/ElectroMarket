/* =====================================================================
   ElectroMarket - Resultados del inspector de estado con IA
   ---------------------------------------------------------------------
   Guarda el último análisis de IA de cada producto: condición sugerida,
   confianza, coherencia con el checklist, alertas y expresiones clave.
   Un producto con coherencia REVISAR no puede quedar VERIFICADO.
   Es seguro ejecutarlo más de una vez.
   ===================================================================== */

USE [ElectroMarket];
GO

SET NOCOUNT ON;
GO

IF OBJECT_ID(N'dbo.InspeccionesIA', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.InspeccionesIA (
        IdProducto          INT            NOT NULL
            CONSTRAINT PK_InspeccionesIA PRIMARY KEY
            CONSTRAINT FK_InspeccionesIA_Productos
            REFERENCES dbo.Productos (IdProducto),
        CondicionSugerida   VARCHAR(30)    NOT NULL
            CONSTRAINT CK_InspeccionesIA_Condicion
            CHECK (CondicionSugerida IN ('COMO_NUEVO', 'BUENO', 'ACEPTABLE')),
        Confianza           DECIMAL(5,4)   NOT NULL
            CONSTRAINT CK_InspeccionesIA_Confianza CHECK (Confianza BETWEEN 0 AND 1),
        Coherencia          VARCHAR(15)    NOT NULL
            CONSTRAINT CK_InspeccionesIA_Coherencia CHECK (Coherencia IN ('COHERENTE', 'REVISAR')),
        Alertas             NVARCHAR(MAX)  NOT NULL,   -- lista JSON de textos
        TerminosClave       NVARCHAR(500)  NULL,       -- lista JSON de expresiones
        VersionModelo       VARCHAR(40)    NOT NULL,
        FechaAnalisis       DATETIME2(0)   NOT NULL
            CONSTRAINT DF_InspeccionesIA_Fecha DEFAULT (SYSDATETIME())
    );
    PRINT 'Tabla InspeccionesIA creada.';
END
ELSE
    PRINT 'La tabla InspeccionesIA ya existe.';
GO
