from datetime import datetime

from pydantic import BaseModel


class ProductOut(BaseModel):
    product_id: int
    category: str
    sub_category: str | None
    product_name: str
    quantity: float
    price: float


class OrderOut(BaseModel):
    order_id: int
    customer_id: int
    order_date: datetime
    order_status: str


class OrderStatusOut(BaseModel):
    order_id: int
    order_status: str


class OrderLineItemOut(BaseModel):
    order_product_id: int
    product_id: int
    product_name: str
    special_priced: bool
    quantity: float
    uom: str
    unit_price: float


class CompleteOrderOut(BaseModel):
    order: OrderOut
    products: list[OrderLineItemOut]


class OrderProductOut(BaseModel):
    order_product_id: int
    order_id: int
    customer_id: int
    product_id: int
    special_priced: bool
    quantity: float
    uom: str


class PaymentOut(BaseModel):
    payment_id: int
    order_id: int
    customer_id: int
    payment_method_id: int
    payment_date: datetime
    payment_amount: float


class InvoiceOut(BaseModel):
    invoice_id: int
    order_id: int
    customer_id: int
    payment_id: int
    invoice_date: datetime
    order_amount: float
    tax_amount: float


class DeliveryOut(BaseModel):
    delivery_id: int
    order_id: int
    customer_id: int
    invoice_id: int
    customer_address_id: int
    delivery_date: datetime | None
    delivery_status: str


class DeliveryStatusOut(BaseModel):
    order_id: int
    delivery_status: str
    delivery_date: datetime | None
