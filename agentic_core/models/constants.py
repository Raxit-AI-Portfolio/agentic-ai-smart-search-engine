ROLE_PERMISSIONS_DELTA = {
    "customer": {
        "api": {"profile", "order", "invoice", "products", "payment"},
        "rag": {"refund_return_policy"},
        "sql": set(),
    },
    "worker": {
        "api": {"inventory", "order_processing"},
        "rag": {"order_processing_sop", "customer_support_sop"},
        "sql": set(),
    },
    "manager": {
        "api": {"special_pricing", "inventory"},
        "rag": {"legal_policies", "financial_policies"},
        "sql": {"cs_schema"},
    },
}
