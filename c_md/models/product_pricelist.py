import datetime

import odoo.exceptions
from odoo import models, fields, api

class PriceListExtend(models.Model):
    _name = "price.list.extend"

    name = fields.Char(string="List Name", required=True)
    date = fields.Date(string="List Date", default=datetime.datetime.today())
    state = fields.Selection(
        [('draft', 'Draft'),
         ('running', 'Running'),
         ('expired', 'Expired')],
        'State', default="draft")

    def assign_customers(self):
        for rec in self.line_ids:
            rec.partner_id_A = self.customers_A
            rec.partner_id_B = self.customers_B
            rec.partner_id_C = self.customers_C
            rec.partner_id_D = self.customers_D
            rec.partner_id_E = self.customers_E
            rec.partner_id_F = self.customers_F

    customers_A = fields.Many2many("res.partner", string="Customers A", relation="table_11", copy=True)
    customers_B = fields.Many2many("res.partner", string="Customers B", relation="table_22", copy=True)
    customers_C = fields.Many2many("res.partner", string="Customers C", relation="table_33", copy=True)
    customers_D = fields.Many2many("res.partner", string="Customers D", relation="table_44", copy=True)
    customers_E = fields.Many2many("res.partner", string="Customers E", relation="table_55", copy=True)
    customers_F = fields.Many2many("res.partner", string="Customers F", relation="table_66", copy=True)

    line_ids = fields.One2many("price.list.extend.line", "price_list_extend_id", string="Price List Lines", copy=True)

    def action_confirm(self):
        exist_previous_pricelist = self.search(['|', ('state', '=', 'running'), ('state', '=', 'draft')])
        if len(exist_previous_pricelist) > 1:
            raise odoo.exceptions.ValidationError("You Must Expire Previous Price List !!!!!!")
        self.state = 'running'
        # no_of_pricelists = {1 : 'A', 2 : 'B', 3 : 'C', 4 : 'D', 5 : 'E', 6 : 'F'}
        pricelist = self.env['product.pricelist']
        customers = self.env['res.partner'].search([('customer_rank', '>', '0')])
        # print(no_of_pricelists, type(no_of_pricelists))
        for customer in customers:
            list = []
            for rec in self.line_ids:
                val = {
                    'applied_on': '1_product',
                    'compute_price': 'fixed',
                    'product_tmpl_id': rec.product_id.id,
                    'fixed_price': rec.price_A if customer in rec.partner_id_A else rec.price_B if customer in rec.partner_id_B else rec.price_C if customer in rec.partner_id_C else rec.price_D if customer in rec.partner_id_D else rec.price_E if customer in rec.partner_id_E else rec.price_F
                }
                list.append((0, 0, val))
            exist = pricelist.search([('name', '=', customer.name)])
            if not exist:
               PL = pricelist.create({
                            'name': customer.name,
                            'item_ids': list,
                            })

            else:
                # exist.selectable = True
                exist.item_ids = [(5, 0, 0)]
                exist.item_ids = list
                print(exist)
                print(customer)
                customer.price_list = exist.id

    def action_expired(self):
        self.state = 'expired'

    def action_reset(self):
        self.state = 'draft'

    def action_clear_products(self):
        self.line_ids = [(5, 0, 0)]



    def action_select_all_products(self):
        self.line_ids = [(5, 0, 0)]
        products = self.env['product.template'].search([('sale_ok', '=', True), ('type', '=', 'product')])
        # print(products)
        # print(self.line_ids)
        line = []
        for rec in products:
            val = {'product_id': rec.id,
                   # 'price_A': 100,
                   }
            line.append((0, 0, val))

        self.line_ids = line
        # print(line)

class PriceListExtendLine(models.Model):
    _name = "price.list.extend.line"

    price_list_extend_id = fields.Many2one("price.list.extend", string="Price List Extend Id")
    product_id = fields.Many2one("product.template", string="Products")
    price_A = fields.Float(string="Price A")
    price_B = fields.Float(string="Price B")
    price_C = fields.Float(string="Price C")
    price_D = fields.Float(string="Price D")
    price_E = fields.Float(string="Price E")
    price_F = fields.Float(string="Price F")
    partner_id_A = fields.Many2many(comodel_name="res.partner", string="Customers A", relation="table_1")
    partner_id_B = fields.Many2many(comodel_name="res.partner", string="Customers B", relation="table_2")
    partner_id_C = fields.Many2many("res.partner", string="Customers C", relation="table_3")
    partner_id_D = fields.Many2many("res.partner", string="Customers D", relation="table_4")
    partner_id_E = fields.Many2many("res.partner", string="Customers E", relation="table_5")
    partner_id_F = fields.Many2many("res.partner", string="Customers F", relation="table_6")