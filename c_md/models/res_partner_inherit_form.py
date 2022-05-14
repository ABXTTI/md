import datetime

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = "res.partner"

    price_list = fields.Many2one("product.pricelist", string="Price List")
    property_product_pricelist = fields.Many2one("product.pricelist", string="Price List", related="price_list", readonly=True)