"""
Errores de negocio de ElectroMarket.

Cada error hereda de una categoría con su código HTTP. Los servicios
lanzan estos errores y app.main los convierte en respuestas JSON con
{"detail": ...}, así las rutas no repiten bloques try/except.
"""


class ErrorAplicacion(Exception):
    """Error de negocio esperado. `detalle` permite responder un objeto."""

    status_code = 400

    def __init__(self, mensaje: str = "", detalle=None):
        super().__init__(mensaje)
        self.detalle = detalle if detalle is not None else mensaje


# Categorías ------------------------------------------------------------

class DatosInvalidos(ErrorAplicacion):
    status_code = 400


class NoAutorizado(ErrorAplicacion):
    status_code = 401


class AccesoDenegado(ErrorAplicacion):
    status_code = 403


class NoEncontrado(ErrorAplicacion):
    status_code = 404


class Conflicto(ErrorAplicacion):
    status_code = 409


# Usuarios --------------------------------------------------------------

class EmailAlreadyExists(Conflicto):
    pass


class InvalidCredentials(NoAutorizado):
    pass


class AccountInactive(AccesoDenegado):
    pass


class UserNotFound(NoEncontrado):
    pass


class UserNotActive(AccesoDenegado):
    pass


# Categorías y productos ------------------------------------------------

class CategoryNotFound(NoEncontrado):
    pass


class CategoryInactive(DatosInvalidos):
    pass


class ProductNotFound(NoEncontrado):
    pass


class ProductForbidden(AccesoDenegado):
    pass


class ProductDeleted(Conflicto):
    pass


class ProductInvalidState(Conflicto):
    pass


class ProductOutOfStock(Conflicto):
    pass


class ImageLimitExceeded(DatosInvalidos):
    pass


class InvalidImage(DatosInvalidos):
    pass


# Carrito, direcciones y compra -----------------------------------------

class OwnProduct(AccesoDenegado):
    pass


class CartProcessed(Conflicto):
    pass


class EmptyCart(DatosInvalidos):
    pass


class AddressNotFound(NoEncontrado):
    pass


class AddressInUse(Conflicto):
    pass


class PurchaseValidationError(Conflicto):
    def __init__(self, problemas: list):
        mensaje = "El carrito contiene productos que no se pueden comprar."
        super().__init__(mensaje, detalle={"mensaje": mensaje, "productos": problemas})
        self.problemas = problemas


# Pedidos, pagos, ventas y envíos ---------------------------------------

class OrderNotFound(NoEncontrado):
    pass


class PaymentNotFound(NoEncontrado):
    pass


class RefundNotFound(NoEncontrado):
    pass


class SaleNotFound(NoEncontrado):
    pass


class ShipmentNotFound(NoEncontrado):
    pass


class ShipmentConflict(Conflicto):
    pass


# Cancelaciones ---------------------------------------------------------

class CancellationNotFound(NoEncontrado):
    pass


class CancellationConflict(Conflicto):
    pass


class CancellationForbidden(AccesoDenegado):
    pass


# Reseñas y vendedores --------------------------------------------------

class SellerNotFound(NoEncontrado):
    pass


class ReviewNotFound(NoEncontrado):
    pass


class ReviewForbidden(AccesoDenegado):
    pass


class ReviewConflict(Conflicto):
    pass


# Devoluciones ----------------------------------------------------------

class ReturnNotFound(NoEncontrado):
    pass


class ReturnForbidden(AccesoDenegado):
    pass


class ReturnConflict(Conflicto):
    pass
