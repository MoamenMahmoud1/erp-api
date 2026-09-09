ROLE_DEFINITIONS = (
    {
        "code": "hq-admin", "name": "HQ Admin", "level": 100, "scope": "company", "requires_shift": False,
        "permission_sets": (("all", "*"),),
    },
    {
        "code": "finance", "name": "Finance", "level": 80, "scope": "company", "requires_shift": False,
        "permission_sets": (("app", "accounting"), ("permissions", ("payments", "view_paymenttransaction"), ("payments", "view_paymentrefund"), ("purchases", "view_purchase"), ("purchases", "view_supplierpayment"))),
    },
    {
        "code": "branch-manager", "name": "Branch Manager", "level": 60, "scope": "branch", "requires_shift": False,
        "permission_sets": (("app", "invoices"), ("app", "purchases"), ("app", "inventory"), ("app", "payments"), ("permissions", ("products", "view_product"), ("customers", "view_customer"), ("suppliers", "view_supplier"), ("accounts", "view_employee"), ("accounts", "view_employeeshift"), ("accounts", "view_all_employee_shifts"), ("organization", "view_site"), ("organization", "view_department"))),
    },
    {
        "code": "shop-manager", "name": "Shop Manager", "level": 50, "scope": "site", "requires_shift": True,
        "permission_sets": (("permissions", ("invoices", "view_invoice"), ("invoices", "add_invoice"), ("invoices", "change_invoice"), ("invoices", "confirm_invoice"), ("invoices", "cancel_invoice"), ("invoices", "return_invoice"), ("invoices", "apply_invoice_coupon"), ("purchases", "view_purchase"), ("purchases", "add_purchase"), ("purchases", "change_purchase"), ("purchases", "confirm_purchase"), ("purchases", "cancel_purchase"), ("purchases", "return_purchase"), ("purchases", "process_supplier_payment"), ("inventory", "view_stockbalance"), ("inventory", "view_stocklocation"), ("inventory", "view_stockmovement"), ("inventory", "transfer_stock"), ("payments", "view_paymenttransaction"), ("payments", "process_collection"), ("payments", "refund_payment"), ("products", "view_product"), ("customers", "view_customer"), ("suppliers", "view_supplier"), ("accounts", "start_employee_shift"), ("accounts", "close_employee_shift"))),
    },
    {
        "code": "salesperson", "name": "Salesperson", "level": 20, "scope": "site", "requires_shift": True,
        "permission_sets": (("permissions", ("invoices", "view_invoice"), ("invoices", "add_invoice"), ("invoices", "change_invoice"), ("invoices", "confirm_invoice"), ("invoices", "return_invoice"), ("products", "view_product"), ("customers", "view_customer"), ("payments", "process_collection"), ("payments", "view_paymenttransaction"), ("inventory", "view_stockbalance"), ("accounts", "start_employee_shift"), ("accounts", "close_employee_shift"))),
    },
    {
        "code": "cashier", "name": "Cashier", "level": 25, "scope": "site", "requires_shift": True,
        "permission_sets": (("permissions", ("invoices", "view_invoice"), ("invoices", "add_invoice"), ("invoices", "change_invoice"), ("invoices", "confirm_invoice"), ("invoices", "return_invoice"), ("products", "view_product"), ("customers", "view_customer"), ("payments", "view_paymenttransaction"), ("payments", "process_collection"), ("payments", "refund_payment"), ("accounts", "start_employee_shift"), ("accounts", "close_employee_shift"))),
    },
    {
        "code": "warehouse-operator", "name": "Warehouse Operator", "level": 30, "scope": "site", "requires_shift": True,
        "permission_sets": (("permissions", ("inventory", "view_stockbalance"), ("inventory", "view_stocklocation"), ("inventory", "view_stockmovement"), ("inventory", "transfer_stock"), ("purchases", "view_purchase"), ("purchases", "add_purchase"), ("purchases", "change_purchase"), ("purchases", "confirm_purchase"), ("purchases", "return_purchase"), ("products", "view_product"), ("accounts", "start_employee_shift"), ("accounts", "close_employee_shift"))),
    },
)
