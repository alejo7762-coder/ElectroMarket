/* =====================================================================
   ElectroMarket - Ciclo de vida de los reembolsos simulados
   ---------------------------------------------------------------------
   Completa la tabla Reembolsos para que cada reembolso pase de
   PENDIENTE a PROCESADO (pasarela simulada) con referencia y fechas.
     - Crea la tabla si no existe.
     - Agrega las columnas que falten: Estado, Referencia,
       FechaSolicitud y FechaProcesado.
     - Ajusta la restricción CHECK de Estado.
   Es seguro ejecutarlo más de una vez.
   ===================================================================== */

SET NOCOUNT ON;
GO

IF OBJECT_ID(N'dbo.Reembolsos', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Reembolsos (
        IdReembolso     INT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Reembolsos PRIMARY KEY,
        IdPago          INT            NOT NULL
            CONSTRAINT FK_Reembolsos_Pagos REFERENCES dbo.Pagos (IdPago),
        IdSolicitud     INT            NOT NULL
            CONSTRAINT FK_Reembolsos_Solicitudes
            REFERENCES dbo.SolicitudesCancelacion (IdSolicitud),
        Valor           DECIMAL(12,2)  NOT NULL
            CONSTRAINT CK_Reembolsos_Valor CHECK (Valor > 0)
    );
    PRINT 'Tabla Reembolsos creada.';
END
GO

IF COL_LENGTH('dbo.Reembolsos', 'Estado') IS NULL
    ALTER TABLE dbo.Reembolsos ADD Estado VARCHAR(15) NOT NULL
        CONSTRAINT DF_Reembolsos_Estado DEFAULT ('PENDIENTE');

IF COL_LENGTH('dbo.Reembolsos', 'Referencia') IS NULL
    ALTER TABLE dbo.Reembolsos ADD Referencia VARCHAR(30) NULL;

IF COL_LENGTH('dbo.Reembolsos', 'FechaSolicitud') IS NULL
    ALTER TABLE dbo.Reembolsos ADD FechaSolicitud DATETIME2(0) NOT NULL
        CONSTRAINT DF_Reembolsos_FechaSolicitud DEFAULT (SYSDATETIME());

IF COL_LENGTH('dbo.Reembolsos', 'FechaProcesado') IS NULL
    ALTER TABLE dbo.Reembolsos ADD FechaProcesado DATETIME2(0) NULL;
GO

/* Restricción de estados: se reemplaza cualquier CHECK previo sobre Estado */
DECLARE @nombre SYSNAME, @sql NVARCHAR(400);

DECLARE checks CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.Reembolsos')
      AND definition LIKE '%\[Estado\]%' ESCAPE '\';

OPEN checks;
FETCH NEXT FROM checks INTO @nombre;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'ALTER TABLE dbo.Reembolsos DROP CONSTRAINT ' + QUOTENAME(@nombre);
    EXEC sp_executesql @sql;
    FETCH NEXT FROM checks INTO @nombre;
END
CLOSE checks;
DEALLOCATE checks;

ALTER TABLE dbo.Reembolsos ADD CONSTRAINT CK_Reembolsos_Estado
    CHECK (Estado IN ('PENDIENTE', 'PROCESADO', 'FALLIDO'));
GO

IF COL_LENGTH('dbo.Reembolsos', 'IdReembolso') IS NULL
    PRINT 'ATENCIÓN: Reembolsos no tiene la columna IdReembolso (clave primaria). Agrégala manualmente.';
ELSE
    PRINT 'Reembolsos lista para el ciclo PENDIENTE -> PROCESADO.';
GO
