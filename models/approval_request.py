from odoo import models, fields, api


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    department = fields.Char(string='Department', compute='_compute_dina_info', store=True, readonly=False)
    section = fields.Char(string='Section', store=True, readonly=False)
    is_dina_pr = fields.Boolean(string='Is Dina PR', compute='_compute_dina_info', store=True)

    @api.depends('request_owner_id', 'category_id')
    def _compute_dina_info(self):
        dina_cat = self.env.ref('purchase_requisition_dina.approval_category_dina_pr', raise_if_not_found=False)
        for req in self:
            req.is_dina_pr = bool(
                (dina_cat and req.category_id == dina_cat) or
                (req.category_id and req.category_id.name == 'Dina Purchase Requisition')
            )
            if not req.department and req.request_owner_id:
                employee = self.env['hr.employee'].search([('user_id', '=', req.request_owner_id.id)], limit=1)
                req.department = employee.department_id.name if employee and employee.department_id else ''

    def _get_dina_report_values(self):
        self.ensure_one()
        dept = self.department or ''
        if not dept and self.request_owner_id:
            emp = self.env['hr.employee'].search([('user_id', '=', self.request_owner_id.id)], limit=1)
            if emp and emp.department_id:
                dept = emp.department_id.name
        if not dept and self.reason and 'Department:' in self.reason:
            parts = self.reason.split('|')
            for part in parts:
                if 'Department:' in part:
                    dept = part.replace('Department:', '').strip()

        section = self.section or ''
        if not section and self.reason and 'Section:' in self.reason:
            parts = self.reason.split('|')
            for part in parts:
                if 'Section:' in part:
                    section = part.replace('Section:', '').strip()

        lines = []
        tot_t = 0.0
        tot_vat = 0.0
        tot_grand = 0.0
        for idx, l in enumerate(self.product_line_ids, 1):
            u_price = l.unit_price or (l.product_id.list_price if l.product_id else 0.0) or (l.product_id.standard_price if l.product_id else 0.0)
            t_price = l.total_price or ((l.quantity or 0.0) * u_price)
            vat = l.vat_15 or (t_price * 0.15)
            grand = l.grand_total or (t_price + vat)
            tot_t += t_price
            tot_vat += vat
            tot_grand += grand
            lines.append({
                'sn': idx,
                'description': l.description or (l.product_id.display_name if l.product_id else ''),
                'qty': l.quantity or 0.0,
                'unit_price': u_price,
                'total_price': t_price,
                'vat_15': vat,
                'grand_total': grand,
                'remark': getattr(l, 'remark', '') or '',
            })

        approved_approvers = self.approver_ids.filtered(lambda a: a.status == 'approved')
        chk_name = ''
        chk_date = ''
        app_name = ''
        app_date = ''
        if len(approved_approvers) >= 2:
            chk_name = approved_approvers[0].user_id.name or ''
            chk_date = approved_approvers[0].write_date.strftime('%d/%m/%Y') if approved_approvers[0].write_date else ''
            app_name = approved_approvers[1].user_id.name or ''
            app_date = approved_approvers[1].write_date.strftime('%d/%m/%Y') if approved_approvers[1].write_date else ''
        elif len(approved_approvers) == 1:
            app_name = approved_approvers[0].user_id.name or ''
            app_date = approved_approvers[0].write_date.strftime('%d/%m/%Y') if approved_approvers[0].write_date else ''

        req_name = self.request_owner_id.name or ''
        req_date = self.date.strftime('%d/%m/%Y') if self.date else (self.create_date.strftime('%d/%m/%Y') if self.create_date else '')

        return {
            'dept': dept,
            'section': section,
            'pr_no': self.reference or self.name or '',
            'date': req_date,
            'lines': lines,
            'total_t_price': tot_t,
            'total_vat': tot_vat,
            'total_grand': tot_grand,
            'req_name': req_name,
            'req_date': req_date,
            'chk_name': chk_name,
            'chk_date': chk_date,
            'app_name': app_name,
            'app_date': app_date,
        }

    def action_print_dina_pr(self):
        self.ensure_one()
        return self.env.ref('approvals.action_report_approval_request').report_action(self)


class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    unit_price = fields.Float(string='U/Price', digits='Product Price', compute='_compute_dina_pricing', store=True, readonly=False)
    total_price = fields.Float(string='T/Price', compute='_compute_dina_pricing', store=True, readonly=False)
    vat_15 = fields.Float(string='VAT 15%', compute='_compute_dina_pricing', store=True, readonly=False)
    grand_total = fields.Float(string='Grand Total', compute='_compute_dina_pricing', store=True, readonly=False)
    remark = fields.Char(string='Remark')

    @api.onchange('product_id')
    def _onchange_product_id_dina_pricing(self):
        for line in self:
            if line.product_id and not line.unit_price:
                line.unit_price = line.product_id.list_price or line.product_id.standard_price or 0.0

    @api.depends('product_id', 'quantity', 'unit_price')
    def _compute_dina_pricing(self):
        for line in self:
            u_price = line.unit_price
            if not u_price and line.product_id:
                u_price = line.product_id.list_price or line.product_id.standard_price or 0.0
                line.unit_price = u_price
            t_price = (line.quantity or 0.0) * (u_price or 0.0)
            vat = t_price * 0.15
            line.total_price = t_price
            line.vat_15 = vat
            line.grand_total = t_price + vat

