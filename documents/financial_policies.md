# eKart Financial Policies

**Document Type:** Internal Policy Reference
**Effective Date:** January 1, 2026
**Owning Team:** Finance & Accounting
**Audience:** Finance, Accounting, Fulfillment Ops, Customer Support leads

## 1. Purpose

This document defines how eKart handles payment capture, refund accounting, chargebacks, seller payouts, and tax collection. It complements the customer-facing terms in [refund_return_policy.md](refund_return_policy.md) by describing the internal financial mechanics behind those customer commitments.

## 2. Payment Capture

- **Authorization vs. Capture:** For prepaid orders (card, digital wallet), payment is *authorized* at checkout but only *captured* (i.e., funds actually collected) once the order transitions to "Processing" in the OMS, confirming inventory availability (see [order_processing_sop.md](order_processing_sop.md) Section 3).
- **Authorization Expiry:** Card authorizations typically expire after 7 days if not captured (varies by issuing bank). If an order remains "On Hold" beyond this window, the OMS automatically re-authorizes the payment method before capture; a failed re-authorization cancels the order line.
- **Split Shipments:** When an order splits into multiple shipments from different fulfillment centers, each shipment is captured as a separate charge against the original authorization once that specific shipment enters "Processing" — this ensures customers are not charged for items still delayed or unavailable.
- **Cash on Delivery (COD):** No electronic capture occurs; the delivery carrier collects payment on eKart's behalf and remits it via the carrier's standard settlement cycle (typically T+3 business days after delivery confirmation).

## 3. Sales Tax and VAT

- Sales tax (US) or VAT/GST (EU, UK, India, and other applicable regions) is calculated at checkout based on the shipping destination and the tax classification of each item.
- Digital goods and services are taxed under destination-based digital-services tax rules where applicable (e.g., EU VAT MOSS-equivalent regime), which may differ from the physical-goods rate in the same region.
- Marketplace sellers are responsible for their own tax remittance in jurisdictions where eKart is not deemed the "marketplace facilitator" for tax purposes; where eKart *is* the deemed facilitator (as in most US states and the EU), eKart collects and remits tax on the seller's behalf and reflects this in seller payout statements.

## 4. Refund Accounting

### 4.1 Refund Triggers and Timing
Refunds are triggered by one of the following events, each initiating the accounting entries below:
1. Return QC completion ("Return Complete" status per [order_processing_sop.md](order_processing_sop.md) Section 9).
2. Support-approved goodwill refund or policy exception ([customer_support_sop.md](customer_support_sop.md) Section 4).
3. Automatic system refund (order cancellation, undeliverable package, lost-in-transit resolution).

### 4.2 Accounting Treatment
- A refund reverses the original revenue recognition entry for the returned item(s), including the proportional tax collected, and is booked as a **contra-revenue** entry (Sales Returns and Allowances) rather than a new expense.
- Shipping charges are refunded only when the return reason is attributable to eKart or the seller (damaged, defective, wrong item, delivery failure); customer-initiated "no longer needed" returns do not refund original shipping charges, consistent with [refund_return_policy.md](refund_return_policy.md).
- Restocking fees deducted per policy are recognized as fee revenue at the time the partial refund is issued, not netted silently against the refund line — this preserves an auditable record of the fee.

### 4.3 Refund Method Reconciliation
| Refund Method | Settlement Path | Reconciliation Frequency |
| :--- | :--- | :--- |
| Original card/wallet | Payment gateway API; matched against original transaction ID | Daily |
| eKart Store Credit | Internal ledger only; no external settlement | Real-time |
| Bank transfer (COD refunds) | Batch file to banking partner | Weekly |

## 5. Seller Payouts

- Marketplace sellers are paid out on a **rolling 14-day cycle**: funds from a delivered order become eligible for payout 14 days after delivery confirmation, provided no return or dispute is open against that order.
- If a return or chargeback is initiated **after** a seller has already been paid out for that order, the refunded/disputed amount is deducted from the seller's next payout cycle rather than requiring the seller to remit funds separately.
- Sellers with a chargeback rate exceeding **1%** of monthly transaction volume are moved to a 30-day payout cycle and subject to a compliance review.

## 6. Chargebacks and Payment Disputes

### 6.1 Definition
A chargeback occurs when a customer disputes a charge directly with their card issuer or bank rather than (or in addition to) contacting eKart support.

### 6.2 Process
1. The payment gateway notifies eKart's Finance team of an incoming chargeback, including the reason code (e.g., "goods not received," "unauthorized transaction," "goods not as described").
2. Finance cross-references the order status, delivery confirmation, and any existing support ticket for that order.
3. If eKart has strong compelling evidence (delivery confirmation with signature, prior support resolution already refunding the customer, etc.), Finance submits a dispute representment to the card network within the issuer's deadline (typically 7–21 days depending on network).
4. If no compelling evidence exists or the claim is valid (e.g., item genuinely not delivered), the chargeback is accepted and no representment is filed.
5. **Double-refund prevention:** Support agents must check for an open chargeback (visible in the OMS as a "Payment Disputed" flag) before issuing any refund on that order — see [customer_support_sop.md](customer_support_sop.md) Section 6.3.

### 6.3 Chargeback Fees
- Card networks charge eKart a fee (typically $15–$25) per chargeback regardless of outcome. This fee is absorbed by eKart for eKart-fulfilled orders and deducted from the seller's payout for seller-fulfilled orders where the chargeback reason is seller-attributable (e.g., item not as described).

## 7. Store Credit Liability

- Issued Store Credit is recorded as a financial liability (deferred revenue) on eKart's balance sheet until redeemed or, where legally permitted, escheated as unclaimed property after the statutory dormancy period (varies by US state, typically 3–5 years; Store Credit does not expire per customer-facing policy, but unclaimed-property law may still require escheatment reporting).
- Promotional Store Credit (issued as a marketing incentive rather than a refund) is tracked separately from refund-issued Store Credit for revenue-recognition purposes, since promotional credit redemption is booked as a discount against revenue rather than a liability settlement.

## 8. Financial Controls and Audit

- All refunds above **$1,000** require a second Finance approver before disbursement, regardless of which support tier initiated the request.
- Monthly reconciliation compares OMS-recorded refunds against actual payment gateway/bank settlement records; discrepancies beyond a $500 aggregate threshold are investigated within 5 business days.
- Transaction and refund records are retained for **7 years** per [legal_policies.md](legal_policies.md) Section 4.3 to satisfy tax audit requirements.

## 9. Related Documents
- [refund_return_policy.md](refund_return_policy.md) — customer-facing refund terms and timelines
- [order_processing_sop.md](order_processing_sop.md) — order and returns lifecycle that triggers financial events
- [customer_support_sop.md](customer_support_sop.md) — agent refund authority limits
- [legal_policies.md](legal_policies.md) — tax, retention, and regulatory obligations
