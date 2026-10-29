from enum import Enum


class PaymentType(str, Enum):
    debit_card = "Debit Card"
    credit_card = "Credit Card"
