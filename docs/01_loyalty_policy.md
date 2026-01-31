Got it — we’ll focus **only on four documents** and make them **long, detailed, and RAG-friendly**:

* **Returns Policy**
* **Refund Policy**
* **Loyalty Policy**
* **Support Policy**

Below are **production-style, long-form markdown docs** you can copy directly into your `docs/` directory.

---

# `docs/01_loyalty_policy.md`

# Loyalty and Customer Treatment Policy (Demo Platform)

## Purpose

This document defines how customers are classified into loyalty tiers and how each tier is treated across support, returns, refunds, and recommendations.
The assistant must always:

* Identify the customer’s tier and mode (optimistic or cautious)
* Apply the correct benefits and restrictions
* Avoid offering benefits not allowed for that tier

---

## Tier Classification Rules (Demo Logic)

Tiers are calculated automatically from customer history:

### Metrics Used

* **Total Spend** (sum of all purchases)
* **Purchase Count** (number of transactions)
* **Average Rating** (mean of available review scores)
* **Rating Coverage** (percentage of purchases with a rating)

### Tier Thresholds (Configurable)

* **VIP**

  * Total spend ≥ high threshold
  * AND average rating ≥ high satisfaction threshold
* **Gold**

  * Total spend ≥ medium threshold OR high purchase frequency
* **Silver**

  * Moderate spend OR moderate purchase frequency
* **Bronze**

  * All other customers

These thresholds may be adjusted by the platform administrator.

---

## Customer Mode

Each customer also has a **Mode**, which affects how strictly policies are applied:

### Optimistic Mode

Assigned when:

* Average rating is high
* Rating coverage is sufficient
* Customer history shows positive engagement

Behavior:

* Offer helpful alternatives proactively
* Prefer solutions that preserve satisfaction
* Use warm, encouraging language
* Provide multiple options when allowed

### Cautious Mode

Assigned when:

* Average rating is low
* Rating coverage is poor
* Customer has many disputes or low satisfaction

Behavior:

* Require stricter validation
* Ask for evidence where applicable
* Enforce timelines and conditions carefully
* Avoid offering exceptions unless explicitly allowed

---

## Tier Benefits Summary

### Bronze

* Standard response time
* Standard return and refund rules
* Customer generally pays return shipping (unless defective)
* Limited goodwill eligibility
* Conservative recommendations

### Silver

* Standard response time
* Some flexibility for store credit in edge cases
* Free return shipping only for defective or wrong items
* Moderate goodwill eligibility
* Personalized but cautious recommendations

### Gold

* Priority support response
* Free return shipping for most eligible returns
* Faster refund handling target
* Goodwill options often available
* Broader recommendations and bundles allowed

### VIP

* Highest priority support
* Free return shipping for eligible returns
* Best available resolution within policy
* Most flexible goodwill handling
* Access to premium recommendations and proactive support

---

## Loyalty-Based Restrictions

* Loyalty benefits cannot override legal or financial compliance rules.
* Loyalty status cannot be used to deny standard consumer rights.
* Fraud or abuse suspends loyalty benefits regardless of tier.

---

## Review Impact on Loyalty

* Consistently low ratings may downgrade a customer’s mode or tier.
* High ratings and consistent purchases may upgrade tier automatically.
* Missing ratings reduce confidence and push toward cautious mode.

---

## What the Assistant Must Say

* Clearly explain tier-based benefits when relevant
* Never claim a benefit is guaranteed unless policy allows
* Always frame loyalty benefits as “available options” rather than promises
