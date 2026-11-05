/* =====================================================================
   ElectroMarket - Datos de perfil para la interfaz gráfica
   ---------------------------------------------------------------------
   Agrega a Usuarios las columnas que pide el formulario de registro:
     - FechaNacimiento
     - Genero
   Es seguro ejecutarlo varias veces.
   ===================================================================== */

SET NOCOUNT ON;
GO

IF COL_LENGTH('dbo.Usuarios', 'FechaNacimiento') IS NULL
BEGIN
    ALTER TABLE dbo.Usuarios ADD FechaNacimiento DATE NULL;
    PRINT 'Columna FechaNacimiento agregada.';
END
ELSE
    PRINT 'La columna FechaNacimiento ya existe.';
GO

IF COL_LENGTH('dbo.Usuarios', 'Genero') IS NULL
BEGIN
    ALTER TABLE dbo.Usuarios ADD Genero VARCHAR(20) NULL;
    PRINT 'Columna Genero agregada.';
END
ELSE
    PRINT 'La columna Genero ya existe.';
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_Usuarios_Genero'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD CONSTRAINT CK_Usuarios_Genero CHECK (
        Genero IS NULL
        OR Genero IN ('MASCULINO', 'FEMENINO', 'OTRO', 'PREFIERO_NO_DECIRLO')
    );
    PRINT 'Restricción CK_Usuarios_Genero creada.';
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE name = 'CK_Usuarios_FechaNacimiento'
)
BEGIN
    ALTER TABLE dbo.Usuarios ADD CONSTRAINT CK_Usuarios_FechaNacimiento CHECK (
        FechaNacimiento IS NULL
        OR FechaNacimiento <= CAST(GETDATE() AS DATE)
    );
    PRINT 'Restricción CK_Usuarios_FechaNacimiento creada.';
END
GO
