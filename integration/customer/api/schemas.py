from pydantic import BaseModel


class UserOut(BaseModel):
    customer_id: int
    first_name: str
    last_name: str
    email: str
    contact_number: str | None


class AddressOut(BaseModel):
    customer_address_id: int
    customer_id: int
    street_line_1: str
    street_line_2: str | None
    city: str
    state: str | None
    country: str
    postal_code: str | None
    is_primary: bool


class PaymentMethodOut(BaseModel):
    payment_method_id: int
    customer_id: int
    payment_type: str
    card_last_four: str
    billing_address: str | None
