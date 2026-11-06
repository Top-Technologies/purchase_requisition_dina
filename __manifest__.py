{
    'name': 'Dina Anbessa Purchase Requisition',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Custom Purchase Requisition with Approval Workflow, Approvals App Integration, and Print Layout',
    'depends': ['base', 'purchase', 'mail', 'approvals'],
    'data': [
        'security/ir.model.access.csv',
        'data/approval_category_data.xml',
        'views/purchase_requisition_views.xml',
        'reports/report_purchase_requisition.xml',
    ],
    'installable': True,
    'application': True,
}