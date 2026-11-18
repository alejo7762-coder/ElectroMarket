USE [master]
GO
/****** Objeto: Database [ElectroMarket] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE DATABASE [ElectroMarket]
 CONTAINMENT = NONE
 ON  PRIMARY 
( NAME = N'ElectroMarket', FILENAME = N'C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\DATA\ElectroMarket.mdf' , SIZE = 8192KB , MAXSIZE = UNLIMITED, FILEGROWTH = 65536KB )
 LOG ON 
( NAME = N'ElectroMarket_log', FILENAME = N'C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS\MSSQL\DATA\ElectroMarket_log.ldf' , SIZE = 8192KB , MAXSIZE = 2048GB , FILEGROWTH = 65536KB )
 WITH CATALOG_COLLATION = DATABASE_DEFAULT, LEDGER = OFF
GO
ALTER DATABASE [ElectroMarket] SET COMPATIBILITY_LEVEL = 170
GO
IF (1 = FULLTEXTSERVICEPROPERTY('IsFullTextInstalled'))
begin
EXEC [ElectroMarket].[dbo].[sp_fulltext_database] @action = 'enable'
end
GO
ALTER DATABASE [ElectroMarket] SET ANSI_NULL_DEFAULT OFF 
GO
ALTER DATABASE [ElectroMarket] SET ANSI_NULLS OFF 
GO
ALTER DATABASE [ElectroMarket] SET ANSI_PADDING OFF 
GO
ALTER DATABASE [ElectroMarket] SET ANSI_WARNINGS OFF 
GO
ALTER DATABASE [ElectroMarket] SET ARITHABORT OFF 
GO
ALTER DATABASE [ElectroMarket] SET AUTO_CLOSE ON 
GO
ALTER DATABASE [ElectroMarket] SET AUTO_SHRINK OFF 
GO
ALTER DATABASE [ElectroMarket] SET AUTO_UPDATE_STATISTICS ON 
GO
ALTER DATABASE [ElectroMarket] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO
ALTER DATABASE [ElectroMarket] SET CURSOR_DEFAULT  GLOBAL 
GO
ALTER DATABASE [ElectroMarket] SET CONCAT_NULL_YIELDS_NULL OFF 
GO
ALTER DATABASE [ElectroMarket] SET NUMERIC_ROUNDABORT OFF 
GO
ALTER DATABASE [ElectroMarket] SET QUOTED_IDENTIFIER OFF 
GO
ALTER DATABASE [ElectroMarket] SET RECURSIVE_TRIGGERS OFF 
GO
ALTER DATABASE [ElectroMarket] SET  ENABLE_BROKER 
GO
ALTER DATABASE [ElectroMarket] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO
ALTER DATABASE [ElectroMarket] SET DATE_CORRELATION_OPTIMIZATION OFF 
GO
ALTER DATABASE [ElectroMarket] SET TRUSTWORTHY OFF 
GO
ALTER DATABASE [ElectroMarket] SET ALLOW_SNAPSHOT_ISOLATION OFF 
GO
ALTER DATABASE [ElectroMarket] SET PARAMETERIZATION SIMPLE 
GO
ALTER DATABASE [ElectroMarket] SET READ_COMMITTED_SNAPSHOT OFF 
GO
ALTER DATABASE [ElectroMarket] SET HONOR_BROKER_PRIORITY OFF 
GO
ALTER DATABASE [ElectroMarket] SET RECOVERY SIMPLE 
GO
ALTER DATABASE [ElectroMarket] SET  MULTI_USER 
GO
ALTER DATABASE [ElectroMarket] SET PAGE_VERIFY CHECKSUM  
GO
ALTER DATABASE [ElectroMarket] SET DB_CHAINING OFF 
GO
ALTER DATABASE [ElectroMarket] SET FILESTREAM( NON_TRANSACTED_ACCESS = OFF ) 
GO
ALTER DATABASE [ElectroMarket] SET TARGET_RECOVERY_TIME = 60 SECONDS 
GO
ALTER DATABASE [ElectroMarket] SET DELAYED_DURABILITY = DISABLED 
GO
ALTER DATABASE [ElectroMarket] SET OPTIMIZED_LOCKING = OFF 
GO
ALTER DATABASE [ElectroMarket] SET ACCELERATED_DATABASE_RECOVERY = OFF  
GO
ALTER DATABASE [ElectroMarket] SET QUERY_STORE = ON
GO
ALTER DATABASE [ElectroMarket] SET QUERY_STORE (OPERATION_MODE = READ_WRITE, CLEANUP_POLICY = (STALE_QUERY_THRESHOLD_DAYS = 30), DATA_FLUSH_INTERVAL_SECONDS = 900, INTERVAL_LENGTH_MINUTES = 60, MAX_STORAGE_SIZE_MB = 1000, QUERY_CAPTURE_MODE = AUTO, SIZE_BASED_CLEANUP_MODE = AUTO, MAX_PLANS_PER_QUERY = 200, WAIT_STATS_CAPTURE_MODE = ON)
GO
USE [ElectroMarket]
GO
/****** Objeto: Table [dbo].[Carritos] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Carritos](
	[IdCarrito] [int] IDENTITY(1,1) NOT NULL,
	[IdUsuario] [int] NOT NULL,
	[FechaCreacion] [datetime2](0) NOT NULL,
	[FechaActualizacion] [datetime2](0) NOT NULL,
	[Estado] [varchar](20) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdCarrito] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Carritos_Usuario] UNIQUE NONCLUSTERED 
(
	[IdUsuario] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Categorias] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Categorias](
	[IdCategoria] [int] IDENTITY(1,1) NOT NULL,
	[Nombre] [varchar](80) NOT NULL,
	[Descripcion] [varchar](250) NULL,
	[Estado] [bit] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdCategoria] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Categorias_Nombre] UNIQUE NONCLUSTERED 
(
	[Nombre] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[DetallesCarrito] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[DetallesCarrito](
	[IdDetalleCarrito] [int] IDENTITY(1,1) NOT NULL,
	[IdCarrito] [int] NOT NULL,
	[IdProducto] [int] NOT NULL,
	[Cantidad] [int] NOT NULL,
	[FechaAgregado] [datetime2](0) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdDetalleCarrito] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Carrito_Producto] UNIQUE NONCLUSTERED 
(
	[IdCarrito] ASC,
	[IdProducto] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[DetalleSolicitudCancelacion] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[DetalleSolicitudCancelacion](
	[IdDetalleSolicitud] [int] IDENTITY(1,1) NOT NULL,
	[IdSolicitud] [int] NOT NULL,
	[IdVenta] [int] NOT NULL,
	[IdDetallePedido] [int] NOT NULL,
	[CantidadSolicitada] [int] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdDetalleSolicitud] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Solicitud_Detalle] UNIQUE NONCLUSTERED 
(
	[IdSolicitud] ASC,
	[IdDetallePedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[DetallesPedido] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[DetallesPedido](
	[IdDetallePedido] [int] IDENTITY(1,1) NOT NULL,
	[IdPedido] [int] NOT NULL,
	[IdProducto] [int] NOT NULL,
	[IdVendedor] [int] NOT NULL,
	[Cantidad] [int] NOT NULL,
	[PrecioUnitario] [decimal](12, 2) NOT NULL,
	[Subtotal] [decimal](12, 2) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdDetallePedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_DetallePedido_Id_Pedido] UNIQUE NONCLUSTERED 
(
	[IdDetallePedido] ASC,
	[IdPedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_DetallePedido_Id_Vendedor] UNIQUE NONCLUSTERED 
(
	[IdDetallePedido] ASC,
	[IdVendedor] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Pedido_Producto] UNIQUE NONCLUSTERED 
(
	[IdPedido] ASC,
	[IdProducto] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[DetalleVenta] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[DetalleVenta](
	[IdDetalleVenta] [int] IDENTITY(1,1) NOT NULL,
	[IdVenta] [int] NOT NULL,
	[IdDetallePedido] [int] NOT NULL,
	[IdVendedor] [int] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdDetalleVenta] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_DetalleVenta_Pedido] UNIQUE NONCLUSTERED 
(
	[IdDetallePedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Venta_DetallePedido] UNIQUE NONCLUSTERED 
(
	[IdVenta] ASC,
	[IdDetallePedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Direcciones] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Direcciones](
	[IdDireccion] [int] IDENTITY(1,1) NOT NULL,
	[IdUsuario] [int] NOT NULL,
	[Direccion] [varchar](250) NOT NULL,
	[Ciudad] [varchar](100) NOT NULL,
	[Departamento] [varchar](100) NOT NULL,
	[CodigoPostal] [varchar](15) NULL,
	[Referencia] [varchar](250) NULL,
	[EsPrincipal] [bit] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdDireccion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Direcciones_Usuario] UNIQUE NONCLUSTERED 
(
	[IdDireccion] ASC,
	[IdUsuario] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Envios] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Envios](
	[IdEnvio] [int] IDENTITY(1,1) NOT NULL,
	[IdVenta] [int] NOT NULL,
	[Transportadora] [varchar](100) NULL,
	[NumeroGuia] [varchar](100) NULL,
	[Estado] [varchar](25) NOT NULL,
	[FechaDespacho] [datetime2](0) NULL,
	[FechaEntrega] [datetime2](0) NULL,
PRIMARY KEY CLUSTERED 
(
	[IdEnvio] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Envios_Venta] UNIQUE NONCLUSTERED 
(
	[IdVenta] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[HistorialEnvios] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[HistorialEnvios](
	[IdHistorialEnvio] [int] IDENTITY(1,1) NOT NULL,
	[IdEnvio] [int] NOT NULL,
	[Estado] [varchar](25) NOT NULL,
	[FechaCambio] [datetime2](0) NOT NULL,
	[Observacion] [varchar](500) NULL,
PRIMARY KEY CLUSTERED 
(
	[IdHistorialEnvio] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[HistorialEstados] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[HistorialEstados](
	[IdHistorial] [int] IDENTITY(1,1) NOT NULL,
	[TipoOperacion] [varchar](20) NOT NULL,
	[IdOperacion] [int] NOT NULL,
	[EstadoAnterior] [varchar](30) NULL,
	[EstadoNuevo] [varchar](30) NOT NULL,
	[FechaCambio] [datetime2](0) NOT NULL,
	[Observacion] [varchar](500) NULL,
PRIMARY KEY CLUSTERED 
(
	[IdHistorial] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[ImagenesProducto] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[ImagenesProducto](
	[IdImagen] [int] IDENTITY(1,1) NOT NULL,
	[IdProducto] [int] NOT NULL,
	[RutaImagen] [varchar](500) NOT NULL,
	[EsPrincipal] [bit] NOT NULL,
	[FechaRegistro] [datetime2](0) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdImagen] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Pagos] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Pagos](
	[IdPago] [int] IDENTITY(1,1) NOT NULL,
	[IdPedido] [int] NOT NULL,
	[Valor] [decimal](12, 2) NOT NULL,
	[Metodo] [varchar](30) NOT NULL,
	[Estado] [varchar](25) NOT NULL,
	[Referencia] [varchar](100) NULL,
	[FechaPago] [datetime2](0) NULL,
PRIMARY KEY CLUSTERED 
(
	[IdPago] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Pagos_Pedido] UNIQUE NONCLUSTERED 
(
	[IdPedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Pedidos] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Pedidos](
	[IdPedido] [int] IDENTITY(1,1) NOT NULL,
	[IdComprador] [int] NOT NULL,
	[IdDireccion] [int] NOT NULL,
	[DireccionEntrega] [varchar](250) NOT NULL,
	[CiudadEntrega] [varchar](100) NOT NULL,
	[DepartamentoEntrega] [varchar](100) NOT NULL,
	[CodigoPostalEntrega] [varchar](15) NULL,
	[FechaPedido] [datetime2](0) NOT NULL,
	[Total] [decimal](12, 2) NOT NULL,
	[Estado] [varchar](30) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdPedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Productos] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Productos](
	[IdProducto] [int] IDENTITY(1,1) NOT NULL,
	[IdVendedor] [int] NOT NULL,
	[IdCategoria] [int] NOT NULL,
	[Nombre] [varchar](150) NOT NULL,
	[Descripcion] [varchar](1000) NOT NULL,
	[Precio] [decimal](12, 2) NOT NULL,
	[Stock] [int] NOT NULL,
	[Estado] [varchar](20) NOT NULL,
	[Condicion] [varchar](30) NOT NULL,
	[FechaPublicacion] [datetime2](0) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdProducto] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Productos_IdProducto_Vendedor] UNIQUE NONCLUSTERED 
(
	[IdProducto] ASC,
	[IdVendedor] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Reembolsos] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Reembolsos](
	[IdReembolso] [int] IDENTITY(1,1) NOT NULL,
	[IdPago] [int] NOT NULL,
	[IdSolicitud] [int] NOT NULL,
	[Valor] [decimal](12, 2) NOT NULL,
	[Estado] [varchar](20) NOT NULL,
	[FechaReembolso] [datetime2](0) NULL,
PRIMARY KEY CLUSTERED 
(
	[IdReembolso] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[SolicitudesCancelacion] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[SolicitudesCancelacion](
	[IdSolicitud] [int] IDENTITY(1,1) NOT NULL,
	[IdPedido] [int] NOT NULL,
	[IdVenta] [int] NULL,
	[IdUsuario] [int] NOT NULL,
	[TipoSolicitud] [varchar](15) NOT NULL,
	[Motivo] [varchar](500) NOT NULL,
	[Estado] [varchar](25) NOT NULL,
	[FechaSolicitud] [datetime2](0) NOT NULL,
	[FechaRespuesta] [datetime2](0) NULL,
PRIMARY KEY CLUSTERED 
(
	[IdSolicitud] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Usuarios] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Usuarios](
	[IdUsuario] [int] IDENTITY(1,1) NOT NULL,
	[Nombre] [varchar](100) NOT NULL,
	[Apellido] [varchar](100) NOT NULL,
	[Correo] [varchar](150) NOT NULL,
	[ContrasenaHash] [varchar](255) NOT NULL,
	[Telefono] [varchar](20) NULL,
	[FechaRegistro] [datetime2](0) NOT NULL,
	[Estado] [varchar](20) NOT NULL,
	[FechaNacimiento] [date] NULL,
	[Genero] [varchar](20) NULL,
PRIMARY KEY CLUSTERED 
(
	[IdUsuario] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Usuarios_Correo] UNIQUE NONCLUSTERED 
(
	[Correo] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Table [dbo].[Ventas] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Ventas](
	[IdVenta] [int] IDENTITY(1,1) NOT NULL,
	[IdPedido] [int] NOT NULL,
	[IdVendedor] [int] NOT NULL,
	[Subtotal] [decimal](12, 2) NOT NULL,
	[Estado] [varchar](25) NOT NULL,
	[FechaVenta] [datetime2](0) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[IdVenta] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Pedido_Vendedor] UNIQUE NONCLUSTERED 
(
	[IdPedido] ASC,
	[IdVendedor] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Venta_Vendedor] UNIQUE NONCLUSTERED 
(
	[IdVenta] ASC,
	[IdVendedor] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Objeto: Index [IX_DetallesPedido_Pedido] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_DetallesPedido_Pedido] ON [dbo].[DetallesPedido]
(
	[IdPedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Objeto: Index [IX_Envios_Estado] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_Envios_Estado] ON [dbo].[Envios]
(
	[Estado] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [IX_HistorialEnvios_Envio] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_HistorialEnvios_Envio] ON [dbo].[HistorialEnvios]
(
	[IdEnvio] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [UX_Imagen_Principal] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE UNIQUE NONCLUSTERED INDEX [UX_Imagen_Principal] ON [dbo].[ImagenesProducto]
(
	[IdProducto] ASC
)
WHERE ([EsPrincipal]=(1))
WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [IX_Pedidos_Comprador] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_Pedidos_Comprador] ON [dbo].[Pedidos]
(
	[IdComprador] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [IX_Productos_Categoria] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_Productos_Categoria] ON [dbo].[Productos]
(
	[IdCategoria] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [IX_Productos_Vendedor] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_Productos_Vendedor] ON [dbo].[Productos]
(
	[IdVendedor] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [IX_Reembolsos_Pago] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_Reembolsos_Pago] ON [dbo].[Reembolsos]
(
	[IdPago] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [IX_Solicitudes_Pedido] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_Solicitudes_Pedido] ON [dbo].[SolicitudesCancelacion]
(
	[IdPedido] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
/****** Objeto: Index [IX_Ventas_Vendedor] Fecha de script: 17/11/2026 10:39:06 p. m. ******/
CREATE NONCLUSTERED INDEX [IX_Ventas_Vendedor] ON [dbo].[Ventas]
(
	[IdVendedor] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
ALTER TABLE [dbo].[Carritos] ADD  DEFAULT (sysdatetime()) FOR [FechaCreacion]
GO
ALTER TABLE [dbo].[Carritos] ADD  DEFAULT (sysdatetime()) FOR [FechaActualizacion]
GO
ALTER TABLE [dbo].[Carritos] ADD  DEFAULT ('ACTIVO') FOR [Estado]
GO
ALTER TABLE [dbo].[Categorias] ADD  DEFAULT ((1)) FOR [Estado]
GO
ALTER TABLE [dbo].[DetallesCarrito] ADD  DEFAULT (sysdatetime()) FOR [FechaAgregado]
GO
ALTER TABLE [dbo].[Direcciones] ADD  DEFAULT ((0)) FOR [EsPrincipal]
GO
ALTER TABLE [dbo].[Envios] ADD  DEFAULT ('PREPARANDO') FOR [Estado]
GO
ALTER TABLE [dbo].[HistorialEnvios] ADD  DEFAULT (sysdatetime()) FOR [FechaCambio]
GO
ALTER TABLE [dbo].[HistorialEstados] ADD  DEFAULT (sysdatetime()) FOR [FechaCambio]
GO
ALTER TABLE [dbo].[ImagenesProducto] ADD  DEFAULT ((0)) FOR [EsPrincipal]
GO
ALTER TABLE [dbo].[ImagenesProducto] ADD  DEFAULT (sysdatetime()) FOR [FechaRegistro]
GO
ALTER TABLE [dbo].[Pagos] ADD  DEFAULT ('SIMULADO') FOR [Metodo]
GO
ALTER TABLE [dbo].[Pagos] ADD  DEFAULT ('PENDIENTE') FOR [Estado]
GO
ALTER TABLE [dbo].[Pedidos] ADD  DEFAULT (sysdatetime()) FOR [FechaPedido]
GO
ALTER TABLE [dbo].[Pedidos] ADD  DEFAULT ('PENDIENTE_PAGO') FOR [Estado]
GO
ALTER TABLE [dbo].[Productos] ADD  DEFAULT ((1)) FOR [Stock]
GO
ALTER TABLE [dbo].[Productos] ADD  DEFAULT ('PUBLICADO') FOR [Estado]
GO
ALTER TABLE [dbo].[Productos] ADD  DEFAULT (sysdatetime()) FOR [FechaPublicacion]
GO
ALTER TABLE [dbo].[Reembolsos] ADD  DEFAULT ('PENDIENTE') FOR [Estado]
GO
ALTER TABLE [dbo].[SolicitudesCancelacion] ADD  DEFAULT ('PENDIENTE') FOR [Estado]
GO
ALTER TABLE [dbo].[SolicitudesCancelacion] ADD  DEFAULT (sysdatetime()) FOR [FechaSolicitud]
GO
ALTER TABLE [dbo].[Usuarios] ADD  DEFAULT (sysdatetime()) FOR [FechaRegistro]
GO
ALTER TABLE [dbo].[Usuarios] ADD  DEFAULT ('ACTIVO') FOR [Estado]
GO
ALTER TABLE [dbo].[Ventas] ADD  DEFAULT ('PENDIENTE') FOR [Estado]
GO
ALTER TABLE [dbo].[Ventas] ADD  DEFAULT (sysdatetime()) FOR [FechaVenta]
GO
ALTER TABLE [dbo].[Carritos]  WITH CHECK ADD  CONSTRAINT [FK_Carritos_Usuarios] FOREIGN KEY([IdUsuario])
REFERENCES [dbo].[Usuarios] ([IdUsuario])
GO
ALTER TABLE [dbo].[Carritos] CHECK CONSTRAINT [FK_Carritos_Usuarios]
GO
ALTER TABLE [dbo].[DetallesCarrito]  WITH CHECK ADD  CONSTRAINT [FK_DetallesCarrito_Carritos] FOREIGN KEY([IdCarrito])
REFERENCES [dbo].[Carritos] ([IdCarrito])
GO
ALTER TABLE [dbo].[DetallesCarrito] CHECK CONSTRAINT [FK_DetallesCarrito_Carritos]
GO
ALTER TABLE [dbo].[DetallesCarrito]  WITH CHECK ADD  CONSTRAINT [FK_DetallesCarrito_Productos] FOREIGN KEY([IdProducto])
REFERENCES [dbo].[Productos] ([IdProducto])
GO
ALTER TABLE [dbo].[DetallesCarrito] CHECK CONSTRAINT [FK_DetallesCarrito_Productos]
GO
ALTER TABLE [dbo].[DetalleSolicitudCancelacion]  WITH CHECK ADD  CONSTRAINT [FK_DetalleSolicitud_DetalleVenta] FOREIGN KEY([IdVenta], [IdDetallePedido])
REFERENCES [dbo].[DetalleVenta] ([IdVenta], [IdDetallePedido])
GO
ALTER TABLE [dbo].[DetalleSolicitudCancelacion] CHECK CONSTRAINT [FK_DetalleSolicitud_DetalleVenta]
GO
ALTER TABLE [dbo].[DetalleSolicitudCancelacion]  WITH CHECK ADD  CONSTRAINT [FK_DetalleSolicitud_Solicitud] FOREIGN KEY([IdSolicitud])
REFERENCES [dbo].[SolicitudesCancelacion] ([IdSolicitud])
GO
ALTER TABLE [dbo].[DetalleSolicitudCancelacion] CHECK CONSTRAINT [FK_DetalleSolicitud_Solicitud]
GO
ALTER TABLE [dbo].[DetallesPedido]  WITH CHECK ADD  CONSTRAINT [FK_DetallesPedido_Pedidos] FOREIGN KEY([IdPedido])
REFERENCES [dbo].[Pedidos] ([IdPedido])
GO
ALTER TABLE [dbo].[DetallesPedido] CHECK CONSTRAINT [FK_DetallesPedido_Pedidos]
GO
ALTER TABLE [dbo].[DetallesPedido]  WITH CHECK ADD  CONSTRAINT [FK_DetallesPedido_ProductoVendedor] FOREIGN KEY([IdProducto], [IdVendedor])
REFERENCES [dbo].[Productos] ([IdProducto], [IdVendedor])
GO
ALTER TABLE [dbo].[DetallesPedido] CHECK CONSTRAINT [FK_DetallesPedido_ProductoVendedor]
GO
ALTER TABLE [dbo].[DetalleVenta]  WITH CHECK ADD  CONSTRAINT [FK_DetalleVenta_DetallePedido] FOREIGN KEY([IdDetallePedido], [IdVendedor])
REFERENCES [dbo].[DetallesPedido] ([IdDetallePedido], [IdVendedor])
GO
ALTER TABLE [dbo].[DetalleVenta] CHECK CONSTRAINT [FK_DetalleVenta_DetallePedido]
GO
ALTER TABLE [dbo].[DetalleVenta]  WITH CHECK ADD  CONSTRAINT [FK_DetalleVenta_Venta] FOREIGN KEY([IdVenta], [IdVendedor])
REFERENCES [dbo].[Ventas] ([IdVenta], [IdVendedor])
GO
ALTER TABLE [dbo].[DetalleVenta] CHECK CONSTRAINT [FK_DetalleVenta_Venta]
GO
ALTER TABLE [dbo].[Direcciones]  WITH CHECK ADD  CONSTRAINT [FK_Direcciones_Usuarios] FOREIGN KEY([IdUsuario])
REFERENCES [dbo].[Usuarios] ([IdUsuario])
GO
ALTER TABLE [dbo].[Direcciones] CHECK CONSTRAINT [FK_Direcciones_Usuarios]
GO
ALTER TABLE [dbo].[Envios]  WITH CHECK ADD  CONSTRAINT [FK_Envios_Ventas] FOREIGN KEY([IdVenta])
REFERENCES [dbo].[Ventas] ([IdVenta])
GO
ALTER TABLE [dbo].[Envios] CHECK CONSTRAINT [FK_Envios_Ventas]
GO
ALTER TABLE [dbo].[HistorialEnvios]  WITH CHECK ADD  CONSTRAINT [FK_HistorialEnvios_Envios] FOREIGN KEY([IdEnvio])
REFERENCES [dbo].[Envios] ([IdEnvio])
GO
ALTER TABLE [dbo].[HistorialEnvios] CHECK CONSTRAINT [FK_HistorialEnvios_Envios]
GO
ALTER TABLE [dbo].[ImagenesProducto]  WITH CHECK ADD  CONSTRAINT [FK_Imagenes_Productos] FOREIGN KEY([IdProducto])
REFERENCES [dbo].[Productos] ([IdProducto])
GO
ALTER TABLE [dbo].[ImagenesProducto] CHECK CONSTRAINT [FK_Imagenes_Productos]
GO
ALTER TABLE [dbo].[Pagos]  WITH CHECK ADD  CONSTRAINT [FK_Pagos_Pedidos] FOREIGN KEY([IdPedido])
REFERENCES [dbo].[Pedidos] ([IdPedido])
GO
ALTER TABLE [dbo].[Pagos] CHECK CONSTRAINT [FK_Pagos_Pedidos]
GO
ALTER TABLE [dbo].[Pedidos]  WITH CHECK ADD  CONSTRAINT [FK_Pedidos_Comprador] FOREIGN KEY([IdComprador])
REFERENCES [dbo].[Usuarios] ([IdUsuario])
GO
ALTER TABLE [dbo].[Pedidos] CHECK CONSTRAINT [FK_Pedidos_Comprador]
GO
ALTER TABLE [dbo].[Pedidos]  WITH CHECK ADD  CONSTRAINT [FK_Pedidos_Direccion] FOREIGN KEY([IdDireccion], [IdComprador])
REFERENCES [dbo].[Direcciones] ([IdDireccion], [IdUsuario])
GO
ALTER TABLE [dbo].[Pedidos] CHECK CONSTRAINT [FK_Pedidos_Direccion]
GO
ALTER TABLE [dbo].[Productos]  WITH CHECK ADD  CONSTRAINT [FK_Productos_Categorias] FOREIGN KEY([IdCategoria])
REFERENCES [dbo].[Categorias] ([IdCategoria])
GO
ALTER TABLE [dbo].[Productos] CHECK CONSTRAINT [FK_Productos_Categorias]
GO
ALTER TABLE [dbo].[Productos]  WITH CHECK ADD  CONSTRAINT [FK_Productos_Usuarios] FOREIGN KEY([IdVendedor])
REFERENCES [dbo].[Usuarios] ([IdUsuario])
GO
ALTER TABLE [dbo].[Productos] CHECK CONSTRAINT [FK_Productos_Usuarios]
GO
ALTER TABLE [dbo].[Reembolsos]  WITH CHECK ADD  CONSTRAINT [FK_Reembolsos_Pagos] FOREIGN KEY([IdPago])
REFERENCES [dbo].[Pagos] ([IdPago])
GO
ALTER TABLE [dbo].[Reembolsos] CHECK CONSTRAINT [FK_Reembolsos_Pagos]
GO
ALTER TABLE [dbo].[Reembolsos]  WITH CHECK ADD  CONSTRAINT [FK_Reembolsos_Solicitudes] FOREIGN KEY([IdSolicitud])
REFERENCES [dbo].[SolicitudesCancelacion] ([IdSolicitud])
GO
ALTER TABLE [dbo].[Reembolsos] CHECK CONSTRAINT [FK_Reembolsos_Solicitudes]
GO
ALTER TABLE [dbo].[SolicitudesCancelacion]  WITH CHECK ADD  CONSTRAINT [FK_Solicitudes_Pedidos] FOREIGN KEY([IdPedido])
REFERENCES [dbo].[Pedidos] ([IdPedido])
GO
ALTER TABLE [dbo].[SolicitudesCancelacion] CHECK CONSTRAINT [FK_Solicitudes_Pedidos]
GO
ALTER TABLE [dbo].[SolicitudesCancelacion]  WITH CHECK ADD  CONSTRAINT [FK_Solicitudes_Usuarios] FOREIGN KEY([IdUsuario])
REFERENCES [dbo].[Usuarios] ([IdUsuario])
GO
ALTER TABLE [dbo].[SolicitudesCancelacion] CHECK CONSTRAINT [FK_Solicitudes_Usuarios]
GO
ALTER TABLE [dbo].[SolicitudesCancelacion]  WITH CHECK ADD  CONSTRAINT [FK_Solicitudes_Ventas] FOREIGN KEY([IdVenta])
REFERENCES [dbo].[Ventas] ([IdVenta])
GO
ALTER TABLE [dbo].[SolicitudesCancelacion] CHECK CONSTRAINT [FK_Solicitudes_Ventas]
GO
ALTER TABLE [dbo].[Ventas]  WITH CHECK ADD  CONSTRAINT [FK_Ventas_Pedidos] FOREIGN KEY([IdPedido])
REFERENCES [dbo].[Pedidos] ([IdPedido])
GO
ALTER TABLE [dbo].[Ventas] CHECK CONSTRAINT [FK_Ventas_Pedidos]
GO
ALTER TABLE [dbo].[Ventas]  WITH CHECK ADD  CONSTRAINT [FK_Ventas_Vendedores] FOREIGN KEY([IdVendedor])
REFERENCES [dbo].[Usuarios] ([IdUsuario])
GO
ALTER TABLE [dbo].[Ventas] CHECK CONSTRAINT [FK_Ventas_Vendedores]
GO
ALTER TABLE [dbo].[Carritos]  WITH CHECK ADD  CONSTRAINT [CK_Carritos_Estado] CHECK  (([Estado]='INACTIVO' OR [Estado]='PROCESADO' OR [Estado]='ACTIVO'))
GO
ALTER TABLE [dbo].[Carritos] CHECK CONSTRAINT [CK_Carritos_Estado]
GO
ALTER TABLE [dbo].[DetallesCarrito]  WITH CHECK ADD  CONSTRAINT [CK_DetallesCarrito_Cantidad] CHECK  (([Cantidad]>(0)))
GO
ALTER TABLE [dbo].[DetallesCarrito] CHECK CONSTRAINT [CK_DetallesCarrito_Cantidad]
GO
ALTER TABLE [dbo].[DetalleSolicitudCancelacion]  WITH CHECK ADD  CONSTRAINT [CK_DetalleSolicitud_Cantidad] CHECK  (([CantidadSolicitada]>(0)))
GO
ALTER TABLE [dbo].[DetalleSolicitudCancelacion] CHECK CONSTRAINT [CK_DetalleSolicitud_Cantidad]
GO
ALTER TABLE [dbo].[DetallesPedido]  WITH CHECK ADD  CONSTRAINT [CK_DetallesPedido_Cantidad] CHECK  (([Cantidad]>(0)))
GO
ALTER TABLE [dbo].[DetallesPedido] CHECK CONSTRAINT [CK_DetallesPedido_Cantidad]
GO
ALTER TABLE [dbo].[DetallesPedido]  WITH CHECK ADD  CONSTRAINT [CK_DetallesPedido_Precio] CHECK  (([PrecioUnitario]>(0)))
GO
ALTER TABLE [dbo].[DetallesPedido] CHECK CONSTRAINT [CK_DetallesPedido_Precio]
GO
ALTER TABLE [dbo].[DetallesPedido]  WITH CHECK ADD  CONSTRAINT [CK_DetallesPedido_Subtotal] CHECK  (([Subtotal]>(0)))
GO
ALTER TABLE [dbo].[DetallesPedido] CHECK CONSTRAINT [CK_DetallesPedido_Subtotal]
GO
ALTER TABLE [dbo].[Envios]  WITH CHECK ADD  CONSTRAINT [CK_Envios_Estado] CHECK  (([Estado]='CANCELADO' OR [Estado]='PROBLEMA' OR [Estado]='ENTREGADO' OR [Estado]='EN_TRANSITO' OR [Estado]='ENVIADO' OR [Estado]='PREPARANDO'))
GO
ALTER TABLE [dbo].[Envios] CHECK CONSTRAINT [CK_Envios_Estado]
GO
ALTER TABLE [dbo].[HistorialEstados]  WITH CHECK ADD  CONSTRAINT [CK_Historial_Tipo] CHECK  (([TipoOperacion]='VENTA' OR [TipoOperacion]='PEDIDO'))
GO
ALTER TABLE [dbo].[HistorialEstados] CHECK CONSTRAINT [CK_Historial_Tipo]
GO
ALTER TABLE [dbo].[Pagos]  WITH CHECK ADD  CONSTRAINT [CK_Pagos_Estado] CHECK  (([Estado]='REEMBOLSADO' OR [Estado]='REEMBOLSO_PARCIAL' OR [Estado]='RECHAZADO' OR [Estado]='APROBADO' OR [Estado]='PENDIENTE'))
GO
ALTER TABLE [dbo].[Pagos] CHECK CONSTRAINT [CK_Pagos_Estado]
GO
ALTER TABLE [dbo].[Pagos]  WITH CHECK ADD  CONSTRAINT [CK_Pagos_Metodo] CHECK  (([Metodo]='TRANSFERENCIA_SIMULADA' OR [Metodo]='TARJETA_SIMULADA' OR [Metodo]='SIMULADO'))
GO
ALTER TABLE [dbo].[Pagos] CHECK CONSTRAINT [CK_Pagos_Metodo]
GO
ALTER TABLE [dbo].[Pagos]  WITH CHECK ADD  CONSTRAINT [CK_Pagos_Valor] CHECK  (([Valor]>(0)))
GO
ALTER TABLE [dbo].[Pagos] CHECK CONSTRAINT [CK_Pagos_Valor]
GO
ALTER TABLE [dbo].[Pedidos]  WITH CHECK ADD  CONSTRAINT [CK_Pedidos_Estado] CHECK  (([Estado]='CANCELADO' OR [Estado]='PARCIALMENTE_CANCELADO' OR [Estado]='CANCELACION_SOLICITADA' OR [Estado]='COMPLETADO' OR [Estado]='PARCIALMENTE_ENVIADO' OR [Estado]='EN_PROCESO' OR [Estado]='PAGADO' OR [Estado]='PENDIENTE_PAGO'))
GO
ALTER TABLE [dbo].[Pedidos] CHECK CONSTRAINT [CK_Pedidos_Estado]
GO
ALTER TABLE [dbo].[Pedidos]  WITH CHECK ADD  CONSTRAINT [CK_Pedidos_Total] CHECK  (([Total]>=(0)))
GO
ALTER TABLE [dbo].[Pedidos] CHECK CONSTRAINT [CK_Pedidos_Total]
GO
ALTER TABLE [dbo].[Productos]  WITH CHECK ADD  CONSTRAINT [CK_Productos_Condicion] CHECK  (([Condicion]='ACEPTABLE' OR [Condicion]='BUENO' OR [Condicion]='COMO_NUEVO'))
GO
ALTER TABLE [dbo].[Productos] CHECK CONSTRAINT [CK_Productos_Condicion]
GO
ALTER TABLE [dbo].[Productos]  WITH CHECK ADD  CONSTRAINT [CK_Productos_Estado] CHECK  (([Estado]='ELIMINADO' OR [Estado]='AGOTADO' OR [Estado]='PAUSADO' OR [Estado]='PUBLICADO'))
GO
ALTER TABLE [dbo].[Productos] CHECK CONSTRAINT [CK_Productos_Estado]
GO
ALTER TABLE [dbo].[Productos]  WITH CHECK ADD  CONSTRAINT [CK_Productos_Precio] CHECK  (([Precio]>(0)))
GO
ALTER TABLE [dbo].[Productos] CHECK CONSTRAINT [CK_Productos_Precio]
GO
ALTER TABLE [dbo].[Productos]  WITH CHECK ADD  CONSTRAINT [CK_Productos_Stock] CHECK  (([Stock]>=(0)))
GO
ALTER TABLE [dbo].[Productos] CHECK CONSTRAINT [CK_Productos_Stock]
GO
ALTER TABLE [dbo].[Reembolsos]  WITH CHECK ADD  CONSTRAINT [CK_Reembolsos_Estado] CHECK  (([Estado]='RECHAZADO' OR [Estado]='PROCESADO' OR [Estado]='PENDIENTE'))
GO
ALTER TABLE [dbo].[Reembolsos] CHECK CONSTRAINT [CK_Reembolsos_Estado]
GO
ALTER TABLE [dbo].[Reembolsos]  WITH CHECK ADD  CONSTRAINT [CK_Reembolsos_Valor] CHECK  (([Valor]>(0)))
GO
ALTER TABLE [dbo].[Reembolsos] CHECK CONSTRAINT [CK_Reembolsos_Valor]
GO
ALTER TABLE [dbo].[SolicitudesCancelacion]  WITH CHECK ADD  CONSTRAINT [CK_Solicitudes_Estado] CHECK  (([Estado]='PROCESADA' OR [Estado]='RECHAZADA' OR [Estado]='APROBADA' OR [Estado]='PENDIENTE'))
GO
ALTER TABLE [dbo].[SolicitudesCancelacion] CHECK CONSTRAINT [CK_Solicitudes_Estado]
GO
ALTER TABLE [dbo].[SolicitudesCancelacion]  WITH CHECK ADD  CONSTRAINT [CK_Solicitudes_Tipo] CHECK  (([TipoSolicitud]='TOTAL' AND [IdVenta] IS NULL OR [TipoSolicitud]='PARCIAL' AND [IdVenta] IS NOT NULL))
GO
ALTER TABLE [dbo].[SolicitudesCancelacion] CHECK CONSTRAINT [CK_Solicitudes_Tipo]
GO
ALTER TABLE [dbo].[Usuarios]  WITH CHECK ADD  CONSTRAINT [CK_Usuarios_Estado] CHECK  (([Estado]='BLOQUEADO' OR [Estado]='INACTIVO' OR [Estado]='ACTIVO'))
GO
ALTER TABLE [dbo].[Usuarios] CHECK CONSTRAINT [CK_Usuarios_Estado]
GO
ALTER TABLE [dbo].[Usuarios]  WITH CHECK ADD  CONSTRAINT [CK_Usuarios_FechaNacimiento] CHECK  (([FechaNacimiento] IS NULL OR [FechaNacimiento]<=CONVERT([date],getdate())))
GO
ALTER TABLE [dbo].[Usuarios] CHECK CONSTRAINT [CK_Usuarios_FechaNacimiento]
GO
ALTER TABLE [dbo].[Usuarios]  WITH CHECK ADD  CONSTRAINT [CK_Usuarios_Genero] CHECK  (([Genero] IS NULL OR ([Genero]='PREFIERO_NO_DECIRLO' OR [Genero]='OTRO' OR [Genero]='FEMENINO' OR [Genero]='MASCULINO')))
GO
ALTER TABLE [dbo].[Usuarios] CHECK CONSTRAINT [CK_Usuarios_Genero]
GO
ALTER TABLE [dbo].[Ventas]  WITH CHECK ADD  CONSTRAINT [CK_Ventas_Estado] CHECK  (([Estado]='CANCELADA' OR [Estado]='CANCELACION_SOLICITADA' OR [Estado]='ENTREGADA' OR [Estado]='ENVIADA' OR [Estado]='PREPARANDO' OR [Estado]='PENDIENTE'))
GO
ALTER TABLE [dbo].[Ventas] CHECK CONSTRAINT [CK_Ventas_Estado]
GO
ALTER TABLE [dbo].[Ventas]  WITH CHECK ADD  CONSTRAINT [CK_Ventas_Subtotal] CHECK  (([Subtotal]>(0)))
GO
ALTER TABLE [dbo].[Ventas] CHECK CONSTRAINT [CK_Ventas_Subtotal]
GO
USE [master]
GO
ALTER DATABASE [ElectroMarket] SET  READ_WRITE 
GO
