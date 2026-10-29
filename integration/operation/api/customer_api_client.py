import httpx
from fastapi import HTTPException, status

from integration.operation.api.config import settings
from integration.shared.enums import PaymentType


async def get_payment_method_ids_by_type(payment_type: PaymentType, authorization_header: str) -> list[int]:
    async with httpx.AsyncClient(base_url=settings.customer_api_base_url) as client:
        try:
            response = await client.get(
                f"/payment-methods/type/{payment_type.value}",
                headers={"Authorization": authorization_header},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="Customer API lookup failed"
            ) from exc
    return [item["payment_method_id"] for item in response.json()]
