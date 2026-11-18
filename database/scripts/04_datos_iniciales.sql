/* =====================================================================
   ElectroMarket - Datos iniciales
   ---------------------------------------------------------------------
   Categorías de productos necesarias para publicar artículos.
   Solo inserta las que no existen; es seguro ejecutarlo varias veces.
   ===================================================================== */

USE [ElectroMarket];
GO

SET NOCOUNT ON;
GO

INSERT INTO dbo.Categorias (Nombre, Descripcion)
SELECT V.Nombre, V.Descripcion
FROM (VALUES
    ('Celulares',          'Teléfonos inteligentes y básicos'),
    ('Computadores',       'Portátiles, equipos de escritorio y tabletas'),
    ('Televisores',        'Televisores y monitores'),
    ('Audio',              'Parlantes, audífonos y equipos de sonido'),
    ('Videojuegos',        'Consolas, controles y accesorios'),
    ('Neveras',            'Neveras y congeladores'),
    ('Lavadoras',          'Lavadoras y secadoras'),
    ('Pequeños electrodomésticos', 'Licuadoras, hornos microondas, cafeteras y similares')
) AS V (Nombre, Descripcion)
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.Categorias C WHERE C.Nombre = V.Nombre
);

PRINT 'Categorías iniciales verificadas.';
GO
