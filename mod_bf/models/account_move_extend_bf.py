# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    def get_previous_and_current_balance(self):
        for rec in self:
            previous = rec.search([('state', '=', 'posted'), ('payment_state', '!=', 'paid'),
                                   ('partner_id', '=', rec.partner_id.id), ('id', '!=', rec.id)])
            if previous:
                for r in previous:
                    rec.previous_balance += r.amount_residual_signed
                    rec.current_balance = rec.previous_balance + rec.amount_residual

            else:
                rec.previous_balance = 0.0
                rec.current_balance = rec.previous_balance + rec.amount_residual

    previous_balance = fields.Float(string="Previous Balance", compute="get_previous_and_current_balance")
    current_balance = fields.Float(string="Current Balance", compute="get_previous_and_current_balance")

    def custom_register_payment(self):
        for rec in self:
            journal_id = rec.env['account.journal'].search([('type', '=', 'cash')])
            print(journal_id)
            values = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_id.id,
                'payment_method_id': 1,
                'amount': self.amount_total,
                'payment_date': self.date,
                'currency_id': 1,
                'journal_id': journal_id.id,
                'communication': self.name,
            }
            account_payment = rec.env['account.payment.register'].with_context(active_ids=rec.ids, active_model="account.move")
            obj = account_payment.create(values)
            obj._create_payments()

    def clear_list_products(self):
        for rec in self:
            rec.line_ids = [(6, 0, 0)]

        for rec in self.invoice_line_ids:
            # print(rec.move_id, self.id)
            if rec.move_id.id == self.id:
                rec.unlink()

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id.restriction_month:
            check = self.search([('state', '=', 'posted'), ('payment_state', '!=', 'not_paid'),
                                ('invoice_date', '<=', datetime.datetime.today() - datetime.timedelta(days=30))])
            if check:
                raise ValidationError("Please Clear Your Dues, since invoice is pending for more than 30 days......!")
        var_customer_name = self.env['customer.name']
        var_customer_code = self.env['customer.code']
        for rec in self:
            vn = var_customer_name.search([('related_partner_id', '=', rec.partner_id.record_id)])
            vc = var_customer_code.search([('related_partner_id', '=', rec.partner_id.record_id)])
            rec.customer_id_generated = vn.id
            rec.customer_code = vc.id

    @api.onchange('customer_id_generated')
    def compute_customer_id(self):
        partner_list = self.env['res.partner']
        var_customer_code = self.env['customer.code']
        for rec in self:
            print("ITs Working")
            partner = partner_list.search([('record_id', '=', rec.customer_id_generated.related_partner_id)])
            vc = var_customer_code.search([('related_partner_id', '=', partner.record_id)])
            rec.customer_code = vc.id
            rec.partner_id = partner.id

    customer_id_generated = fields.Many2one("customer.name", string="Customer ID")

    @api.onchange('customer_code')
    def compute_customer_code(self):
        partner_list = self.env['res.partner']
        var_customer_code = self.env['customer.name']
        for rec in self:
            partner = partner_list.search([('record_id', '=', rec.customer_code.related_partner_id)])
            vn = var_customer_code.search([('related_partner_id', '=', partner.record_id)])
            rec.customer_id_generated = vn.id
            rec.partner_id = partner.id

    customer_code = fields.Many2one("customer.code", string="Customer Code")

    def action_reverse_check(self):
        action = self.env.ref('account.action_view_account_move_reversal').read()[0]
        if self.is_invoice():
            action['name'] = _('Credit Note')

            # create Journal if not exist
            journals = self.env['account.journal'].search([('name', '=', 'Return Inward')])
            if not journals:
                journals.create({
                    'name': 'Return Inward',
                    'type': 'sale',
                    'code': 'RI/SR',
                })
            # create operation type in inventory
            operation_type = self.env['stock.picking.type'].search([('name', '=', 'Return Inward')])
            if not operation_type:
                created = operation_type.create({
                                    'name': 'Return Inward',
                                    'code': 'incoming',
                                    'sequence_code': 'ST/RI',
                                    'warehouse_id': 1,
                                })
        return action

    is_return = fields.Boolean(string="IS Return")

    # Overriding action_post method.....
    def action_post(self):
        """To check the selected customers due amount is exceed than
        blocking stage"""
        pay_type = ['out_invoice', 'out_refund', 'out_receipt']
        for rec in self:
            if rec.partner_id.active_limit and rec.move_type in pay_type \
                    and rec.partner_id.enable_credit_limit:
                if rec.due_amount >= rec.partner_id.blocking_stage:
                    if rec.partner_id.blocking_stage != 0:
                        raise UserError(_(
                            "%s is in  Blocking Stage and "
                            "has a due amount of %s %s to pay") % (
                                            rec.partner_id.name, rec.due_amount,
                                            rec.currency_id.symbol))

    # adding inventory move ---------------------------------------
    #     record = None
        if self.is_return and self.move_type == "out_refund" and self.state == 'draft':
            picking = self.env['stock.picking']
            lines = self.invoice_line_ids
            print(lines, self.id)
            list = []
            for line in lines:
                if line.product_id.type == 'product':
                    vals = {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'name': line.product_id.name,
                        'product_uom': line.product_id.uom_id,
                        'quantity_done': line.quantity,
                    }
                    list.append((0, 0, vals))
            record = picking.create({
                'move_type': 'direct',
                'picking_type_id': 7,
                'location_id': 5,
                'location_dest_id': 8,
                'partner_id': self.partner_id.id,
                'origin': 'ACTUAL RETURN',
                'related_invoice_ids': self.id,
                'move_ids_without_package': list,
            })
            record.action_assign()
            record.button_validate()

        elif self.move_type == 'out_invoice':
            print("Line Number ################ 161 ######################")
            stock_picking = self.env['stock.picking']
            lines = self.invoice_line_ids
            print("Line Number ################ 164 ######################")

            list = []
            for line in lines:
                if line.product_id.type == 'product':
                    vals = {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'name': line.product_id.name,
                        'product_uom': line.product_id.uom_id,
                        'quantity_done': line.quantity,
                    }
                    list.append((0, 0, vals))
                    print("Line Number ################ 177 ######################")
            if list:
                vals = {
                    'partner_id': self.partner_id.id,
                    'move_type': 'direct',
                    'picking_type_id': 2,
                    'location_id': 8,
                    'location_dest_id': 5,
                    'origin': self.name,
                    'related_invoice_ids': self.id,
                    'move_ids_without_package': list
                }
                print(vals)
                record = self.env['stock.picking'].create(vals)
                print("Line Number ################ 188 ######################")
                record.action_assign()
                record.button_validate()
    # added inventory move -----------------------------
        return {
            super(AccountMove, self).action_post(),
            self.custom_register_payment() if self.partner_id.is_cash else "",
        }

    def button_draft(self):
        count = 0
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id:
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft'})

        # RETURN STOCK MOVE*****************
        if self.move_type == "out_invoice" and self.state == 'draft':
            picking = self.env['stock.picking']
            lines = self.invoice_line_ids
            list = []
            for line in lines:
                if line.product_id.type == 'product':
                    vals = {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'name': line.product_id.name,
                        'product_uom': line.product_id.uom_id,
                        'quantity_done': line.quantity,
                    }
                    list.append((0, 0, vals))
            print(list)

            if list:
                record = picking.create({
                    'move_type': 'direct',
                    'picking_type_id': 7,
                    'location_id': 5,
                    'location_dest_id': 8,
                    'partner_id': self.partner_id.id,
                    'origin': 'NOT ACTUAL RETURN',
                    'related_invoice_ids': self.id,
                    'move_ids_without_package': list,
                })
                record.action_assign()
                record.button_validate()
        elif self.move_type == "out_refund":
            raise ValidationError("You Cannot Reset the Return Invoice")

    def compute_total_qty(self):
        for rec in self:
            for t in rec.invoice_line_ids:
                rec.total_qty += t.quantity

    total_qty = fields.Integer(string="Total Qty.", compute="compute_total_qty")