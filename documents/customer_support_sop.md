# eKart Customer Support — Standard Operating Procedure

**Document Type:** Internal SOP
**Effective Date:** January 1, 2026
**Owning Team:** Customer Experience & Trust
**Audience:** Support agents (Tier 1–3), team leads, quality analysts

## 1. Purpose

This SOP standardizes how customer support agents handle inbound contacts — chat, email, phone, and social media — across the full range of eKart customer issues. It defines channel SLAs, ticket categorization, escalation paths, and agent authority limits so that customers receive consistent resolutions regardless of which agent or channel they use.

## 2. Support Channels and Response SLAs

| Channel | First Response SLA | Resolution SLA |
| :--- | :--- | :--- |
| Live Chat | < 60 seconds | < 20 minutes (single session) |
| In-App Help / Email | < 4 hours | < 24 hours |
| Phone | < 2 minutes hold time | Resolved on call where possible |
| Social Media (public mentions/DMs) | < 30 minutes | Moved to private channel (chat/email) within 1 hour |

Support operates **24/7** for Live Chat and Phone in English; regional-language support is available 7:00 AM–11:00 PM local time in each supported market.

## 3. Ticket Categorization

Every contact is logged as a ticket and tagged with one primary category, used for routing and reporting:

1. **Order Status** — "Where is my order," delivery estimates, tracking issues.
2. **Returns & Refunds** — return initiation, refund status, damaged/incorrect items.
3. **Payments & Billing** — failed charges, duplicate charges, invoice requests.
4. **Account & Access** — login issues, password resets, account recovery.
5. **Product & Listing** — product questions, availability, seller inquiries.
6. **Complaints & Escalations** — service complaints, repeated issues, legal/regulatory threats.
7. **Fraud & Security** — suspected account compromise, unauthorized orders, phishing reports.

Category 7 (Fraud & Security) is always routed directly to the Trust & Safety queue regardless of the channel it arrived on, bypassing standard Tier 1 triage.

## 4. Tier Structure and Authority Limits

### Tier 1 (Frontline Agents)
- Handle Order Status, standard Returns & Refunds (within stated policy), Account & Access, and general Product questions.
- Authority to approve standard refunds up to **$150** without lead approval, provided the request falls within [refund_return_policy.md](refund_return_policy.md) eligibility.
- Authority to extend a return window by up to **7 days** for a documented delivery delay (e.g., carrier delay confirmed in tracking).
- May issue Store Credit "goodwill" gestures up to **$25** per customer per rolling 90 days for minor service failures (e.g., a delayed response), without needing a return.

### Tier 2 (Senior Agents / Specialists)
- Handle escalations from Tier 1, Payments & Billing disputes, and complex multi-order issues.
- Authority to approve refunds up to **$750**.
- Authority to authorize policy exceptions described in [refund_return_policy.md](refund_return_policy.md) Section 7, up to a 14-day return window extension.
- Handle chargebacks and payment gateway disputes in coordination with the Finance team (see [financial_policies.md](financial_policies.md) Section 6).

### Tier 3 (Team Leads / Trust & Safety)
- Handle Fraud & Security tickets, legal/regulatory complaints, and any request exceeding Tier 2 authority.
- Authority to approve refunds of any amount with documented justification.
- Sole authority to close, suspend, or reinstate customer accounts.
- Coordinate directly with Legal for any contact that references litigation, regulatory bodies (e.g., consumer protection agencies), or data protection requests (see [legal_policies.md](legal_policies.md) Section 4).

## 5. Escalation Matrix

| Trigger | Escalate To | Target Response Time |
| :--- | :--- | :--- |
| Refund request exceeds agent's authority limit | Next tier up | Within current SLA for the channel |
| Customer requests to speak with a manager | Team Lead (Tier 3) | < 15 minutes on live channels |
| Customer references legal action, a lawyer, or a regulator | Tier 3 + Legal notified automatically | Immediate |
| Suspected account takeover or unauthorized order | Trust & Safety (Tier 3) | Immediate; account temporarily locked pending review |
| Repeat contact (3rd+ time) on the same unresolved issue | Team Lead review, regardless of category | Within 4 hours |
| Customer reports a safety issue with a physical product | Team Lead + Product Safety team | Immediate |

## 6. Standard Resolution Workflows

### 6.1 "Where Is My Order" (WISMO)
1. Pull up the order in the OMS and check current status against the SLA table in [order_processing_sop.md](order_processing_sop.md) Section 10.
2. If within SLA: share the tracking link and current carrier status; no further action needed.
3. If SLA breached: check for an open delivery exception (Section 7 of [order_processing_sop.md](order_processing_sop.md)). Communicate the specific exception and revised estimate.
4. If tracking shows no movement for 5+ days: initiate a carrier trace and offer the customer the choice of waiting for trace results or an immediate reshipment/refund per policy.

### 6.2 Return / Refund Request
1. Confirm the item and reason are eligible under [refund_return_policy.md](refund_return_policy.md).
2. If eligible, initiate the return in the OMS on the customer's behalf (or walk them through self-service) and confirm the refund method and expected timeline per policy Section 3.
3. If the customer disputes eligibility (e.g., past the return window due to a claimed delivery delay), verify the claim against tracking data before making a goodwill exception decision within the agent's authority tier.

### 6.3 Payment Dispute
1. Verify the transaction in the payment gateway dashboard — confirm whether it was a single authorization, a duplicate charge, or a legitimate separate order.
2. Duplicate/erroneous charges are refunded immediately upon confirmation; no need to wait for customer to file a bank chargeback.
3. If the customer has already filed a chargeback with their bank, do not issue a duplicate refund — flag the ticket for Finance reconciliation (see [financial_policies.md](financial_policies.md) Section 6) and inform the customer the chargeback is being processed by their bank.

### 6.4 Account Access Issues
1. Verify identity using two of: registered email, registered phone number, last order ID, or billing zip code.
2. Never reset a password or share account details based on identity claims alone without at least two-factor verification as above.
3. If the account shows signs of compromise (password reset from unrecognized device, orders the customer didn't place), route immediately to Trust & Safety per Section 5 and do not attempt to resolve at Tier 1.

## 7. Quality Assurance

- 5% of all resolved tickets are randomly sampled weekly for QA review against this SOP.
- QA scoring covers: accuracy of resolution, adherence to authority limits, tone/empathy, and SLA compliance.
- Agents scoring below 85% on two consecutive QA cycles are placed on a coaching plan with their team lead.

## 8. Prohibited Agent Actions

Agents at any tier must **never**:
- Promise a refund amount or timeline outside of what policy or their authority tier permits.
- Ask a customer for their full card number, CVV, or password over any channel.
- Process a refund to a payment method different from the original one without Tier 3 approval and identity re-verification.
- Share another customer's order or account information, even to a caller claiming to be a family member, without that customer's own verification.
- Close a ticket as "Resolved" without customer confirmation on Phone/Chat, or without a customer reply/timeout on Email (72-hour auto-close applies only after two follow-up attempts).

## 9. Related Documents
- [refund_return_policy.md](refund_return_policy.md) — refund/return eligibility rules agents apply
- [order_processing_sop.md](order_processing_sop.md) — order lifecycle and delivery exception definitions
- [financial_policies.md](financial_policies.md) — chargeback handling and refund accounting
- [legal_policies.md](legal_policies.md) — data protection requests and regulatory complaint handling
