# eKart Order Processing — Standard Operating Procedure

**Document Type:** Internal SOP
**Effective Date:** January 1, 2026
**Owning Team:** Fulfillment Operations
**Audience:** Fulfillment center staff, warehouse managers, operations analysts

## 1. Purpose

This SOP defines the end-to-end lifecycle of an order from the moment it is placed to the moment it is delivered (or returned), including the handoffs between the order management system, warehouse management system (WMS), and carrier network. It exists to ensure consistent handling, accurate status tracking, and predictable SLAs across all fulfillment centers (FCs).

## 2. Order Lifecycle Overview

Every order progresses through the following statuses, in order. An order may branch into "On Hold," "Cancelled," or "Returned" from most stages.

```
Placed → Payment Confirmed → Processing → Picked → Packed → Shipped → Out for Delivery → Delivered
```

### 2.1 Status Definitions
| Status | Definition | Typical Duration |
| :--- | :--- | :--- |
| Placed | Customer has submitted the order; not yet payment-verified. | < 1 minute |
| Payment Confirmed | Payment gateway has authorized/captured funds (or COD order validated). | < 5 minutes |
| Processing | Order allocated to a fulfillment center and queued for picking. | 1–4 hours |
| Picked | Warehouse staff have physically retrieved all items for the order. | Same day as Processing |
| Packed | Items boxed, labeled, and staged for carrier pickup. | Within 4 hours of Picked |
| Shipped | Carrier has scanned the package into their network. | — |
| Out for Delivery | Package is on a delivery vehicle for final-mile delivery. | Final day of transit |
| Delivered | Carrier confirms handoff to customer (signature, photo, or doorstep drop per delivery preference). | — |

## 3. Order Intake and Payment Verification

1. Order is received by the Order Management System (OMS) and assigned a unique Order ID.
2. OMS performs an automated fraud-risk check (velocity checks, mismatched billing/shipping address flags, high-value first-time-buyer flags).
   - **Low risk:** proceeds automatically to payment capture.
   - **Medium risk:** routed to the Trust & Safety queue for manual review within 2 hours.
   - **High risk:** order automatically placed "On Hold" and customer is notified that additional verification is required.
3. For prepaid orders, payment is authorized at order placement and **captured** only when the order moves to "Processing" (i.e., inventory is confirmed available).
4. For Cash on Delivery (COD) orders, a soft address/phone verification is performed; COD is disabled automatically for accounts with more than 2 refused COD deliveries in the trailing 90 days.

## 4. Inventory Allocation

- The OMS allocates each order line to the nearest fulfillment center carrying sufficient stock, factoring in delivery SLA promised at checkout.
- If an item is out of stock at the nearest FC but available at a secondary FC within the same delivery region, the order is split into multiple shipments and the customer is notified of a multi-package delivery.
- If an item cannot be sourced from any FC within 24 hours, the order line is automatically cancelled, the customer is notified, and any captured payment for that line is refunded per [financial_policies.md](financial_policies.md) Section 4.

## 5. Picking and Packing

### 5.1 Picking
- Pick lists are batched by warehouse zone to minimize walk time; standard target is 95% of pick lists completed within 4 hours of order allocation.
- Pickers scan each item's barcode against the pick list on their handheld device; a mismatch triggers an immediate exception flag and removes the item from that pick run.

### 5.2 Packing
- Packing stations verify item count and condition against the packing slip before sealing.
- Fragile and electronics items require an additional layer of protective packaging per the FC's packing matrix.
- Multi-item orders are consolidated into a single package where size/weight allows; oversized or hazardous items ship separately by default.
- Each package receives a shipping label with a carrier tracking number, which is written back to the OMS and immediately visible to the customer in "My Orders."

## 6. Carrier Handoff and Shipping

- Packed orders are staged in the outbound dock and manifested to the assigned carrier by the FC's scheduled daily cutoff time (varies by FC, typically 6:00 PM local time).
- Orders packed after the daily cutoff roll to the next carrier pickup window; this is reflected in the customer-facing delivery estimate at checkout, so it does not constitute a delay.
- Carrier selection is determined automatically based on package weight/dimensions, delivery distance, and the delivery speed tier the customer selected (Standard, Express, Same-Day where available).

## 7. Delivery Exceptions

| Exception | Standard Handling |
| :--- | :--- |
| Failed delivery attempt (customer unavailable) | Carrier attempts up to 2 additional deliveries on the following business days; customer is notified via app/email/SMS after each attempt. |
| Address undeliverable | Package is held at the carrier's local facility for 5 business days pending customer correction of address; if uncorrected, package is returned to the originating FC and the order is refunded minus original shipping cost. |
| Package lost in transit | If a package shows no tracking movement for 5 consecutive days, Fulfillment Ops opens a carrier trace request. If unresolved after 3 business days, the order is treated as lost: customer is offered a full refund or a reshipment at no charge. |
| Damaged in transit | Customer-reported transit damage follows the process in [refund_return_policy.md](refund_return_policy.md) Section 2.4; Fulfillment Ops separately files a carrier damage claim for internal cost recovery. |
| Wrong item shipped | Immediate replacement order is created at no cost, and a prepaid return label is issued for the incorrect item; no need to wait for the incorrect item's return before the replacement ships. |

## 8. Order Cancellations (Operations View)

- Cancellations submitted by the customer before "Processing" begins are handled entirely within OMS with no warehouse involvement — inventory is simply released back to available stock.
- Cancellations submitted after "Picked" but before "Shipped" require warehouse staff to intercept the package at the pack station and return the items to shelf stock; this is logged as an "Intercepted Cancellation" for inventory audit purposes.
- Cancellations cannot be processed once an order reaches "Shipped" — the order must instead follow the return process in [refund_return_policy.md](refund_return_policy.md).

## 9. Returns Intake at the Fulfillment Center

1. Returned packages are received at the FC's dedicated returns dock and scanned against the return authorization created by the customer (see [refund_return_policy.md](refund_return_policy.md) Section 4).
2. Quality Control (QC) inspects the item against the stated return reason within 2 business days of receipt:
   - **Resalable condition:** item is restocked to available inventory.
   - **Damaged/used beyond resale:** item is routed to the liquidation/write-off pipeline; a partial refund may be applied per policy.
   - **Item does not match what was shipped back (fraud signal):** flagged to Trust & Safety and refund is held pending investigation.
3. Once QC clears the return, the OMS is updated to "Return Complete," which triggers the refund workflow described in [financial_policies.md](financial_policies.md) Section 4.

## 10. Service Level Agreements (SLAs)

| Metric | Target |
| :--- | :--- |
| Order → Processing | < 4 hours (99th percentile) |
| Processing → Shipped | < 24 hours (95th percentile) |
| Standard delivery (Shipped → Delivered) | 3–5 business days |
| Express delivery (Shipped → Delivered) | 1–2 business days |
| Return receipt → QC inspection complete | < 2 business days |
| QC complete → Refund initiated | < 1 business day |

## 11. Escalation

Any order stuck in a single status for longer than 2x its target SLA is automatically flagged in the Fulfillment Ops dashboard and assigned to a shift lead for manual investigation. Repeated SLA breaches at a given FC (more than 5% of daily volume in a week) trigger a formal review with that FC's operations manager.

## 12. Related Documents
- [refund_return_policy.md](refund_return_policy.md) — customer-facing return eligibility and refund terms
- [customer_support_sop.md](customer_support_sop.md) — how support agents interact with order status on the customer's behalf
- [financial_policies.md](financial_policies.md) — payment capture, refund accounting, and reconciliation
