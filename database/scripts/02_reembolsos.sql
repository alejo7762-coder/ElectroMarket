/* =====================================================================
   ElectroMarket - Ciclo de vida de los reembolsos simulados
   ---------------------------------------------------------------------
   La tabla Reembolsos ya existe en el modelo (00_modelo.sql) con
   Estado (PENDIENTE, PROCESADO, RECHAZADO) y FechaReembolso.
   Este script solo agrega las dos columnas que usa la pasarela simulada:
     - FechaSolicitud: cuándo se registró el reembolso (para simular
       el tiempo de procesamiento).
     - Referencia: código RMB-######## asignado al procesarlo.
   Pagos.Estado ya admite REEMBOLSO_PARCIAL y REEMBOLSADO.
   Es seguro ejecutarlo más de una vez.
   ===================================================================== */

USE [ElectroMarket];
GO

SET NOCOUNT ON;
GO

IF COL_LENGTH('dbo.Reembolsos', 'FechaSolicitud') IS NULL
BEGIN
    ALTER TABLE dbo.Reembolsos ADD FechaSolicitud DATETIME2(0) NOT NULL
        CONSTRAINT DF_Reembolsos_FechaSolicitud DEFAULT (SYSDATETIME());
    PRINT 'Columna Reembolsos.FechaSolicitud agregada.';
END

IF COL_LENGTH('dbo.Reembolsos', 'Referencia') IS NULL
BEGIN
    ALTER TABLE dbo.Reembolsos ADD Referencia VARCHAR(30) NULL;
    PRINT 'Columna Reembolsos.Referencia agregada.';
END
GO

PRINT 'Reembolsos lista para el ciclo PENDIENTE -> PROCESADO.';
GO
