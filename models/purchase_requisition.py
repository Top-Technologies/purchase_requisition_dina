from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseRequisitionDina(models.Model):
    _name = 'purchase.requisition.dina'
    _description = 'Dina Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='PR No', required=True, copy=False, readonly=True, default='New')
    department = fields.Char(string='Dept', required=True, tracking=True)
    section = fields.Char(string='Section', tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True, tracking=True)

    line_ids = fields.One2many(
        'purchase.requisition.dina.line',
        'requisition_id',
        string='Requisition Lines'
    )

    approval_request_id = fields.Many2one('approval.request', string='Approval Request', copy=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Requested'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True, index=True)

    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user,
                                   tracking=True)
    requested_date = fields.Date(string='Request Date', default=fields.Date.today)

    checked_by = fields.Many2one('res.users', string='Checked By', tracking=True)
    checked_date = fields.Date(string='Checked Date')

    approved_by = fields.Many2one('res.users', string='Approved By', tracking=True)
    approved_date = fields.Date(string='Approved Date')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition.dina') or 'New'
        return super(PurchaseRequisitionDina, self).create(vals_list)

    def action_create_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            category = self.env.ref('purchase_requisition_dina.approval_category_dina_pr', raise_if_not_found=False)
            if not category:
                category = self.env['approval.category'].search([('name', 'ilike', 'Dina Purchase Requisition')],
                                                                limit=1)

            approval_vals = {
                'name': f"Purchase Requisition: {self.name} ({self.department})",
                'category_id': category.id if category else False,
                'request_owner_id': self.requested_by.id or self.env.user.id,
                'reason': f"Department: {self.department} | Section: {self.section}",
            }
            approval = self.env['approval.request'].create(approval_vals)
            self.approval_request_id = approval.id

    def action_check(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("You cannot check a requisition without any item lines.")
            rec.action_create_approval_request()
            rec.checked_by = self.env.user.id
            rec.checked_date = fields.Date.today()
            rec.state = 'checked'

    def action_approve(self):
        for rec in self:
            rec.approved_by = self.env.user.id
            rec.approved_date = fields.Date.today()
            rec.state = 'approved'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_print_requisition(self):
        self.ensure_one()
        return self.env.ref('purchase_requisition_dina.action_report_purchase_requisition_dina').report_action(self)

    def _get_dina_report_values(self):
        self.ensure_one()
        lines = []
        tot_t = 0.0
        tot_vat = 0.0
        tot_grand = 0.0
        for idx, l in enumerate(self.line_ids, 1):
            tot_t += l.total_price
            tot_vat += l.vat_15
            tot_grand += l.grand_total
            lines.append({
                'sn': idx,
                'description': l.description or '',
                'qty': l.qty or 0.0,
                'unit_price': l.unit_price or 0.0,
                'total_price': l.total_price or 0.0,
                'vat_15': l.vat_15 or 0.0,
                'grand_total': l.grand_total or 0.0,
                'remark': l.remark or '',
            })

        return {
            'dept': self.department or '',
            'section': self.section or '',
            'pr_no': self.name or '',
            'date': self.date.strftime('%d/%m/%Y') if self.date else '',
            'lines': lines,
            'total_t_price': tot_t,
            'total_vat': tot_vat,
            'total_grand': tot_grand,
            'req_name': self.requested_by.name if self.requested_by else '',
            'req_date': self.requested_date.strftime('%d/%m/%Y') if self.requested_date else '',
            'chk_name': self.checked_by.name if self.checked_by else '',
            'chk_date': self.checked_date.strftime('%d/%m/%Y') if self.checked_date else '',
            'app_name': self.approved_by.name if self.approved_by else '',
            'app_date': self.approved_date.strftime('%d/%m/%Y') if self.approved_date else '',
        }


class PurchaseRequisitionDinaLine(models.Model):
    _name = 'purchase.requisition.dina.line'
    _description = 'Purchase Requisition Line'

    requisition_id = fields.Many2one('purchase.requisition.dina', string='Requisition Reference', ondelete='cascade')
    description = fields.Char(string='Description', required=True)
    qty = fields.Float(string='Qty', default=1.0, required=True)
    unit_price = fields.Float(string='U/Price', required=True)
    total_price = fields.Float(string='T/Price', compute='_compute_totals', store=True)
    vat_15 = fields.Float(string='VAT 15%', compute='_compute_totals', store=True)
    grand_total = fields.Float(string='Grand Total', compute='_compute_totals', store=True)
    remark = fields.Char(string='Remark')

    @api.depends('qty', 'unit_price')
    def _compute_totals(self):
        for line in self:
            t_price = line.qty * line.unit_price
            vat = t_price * 0.15
            line.total_price = t_price
            line.vat_15 = vat
            line.grand_total = t_price + vat