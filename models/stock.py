# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'am_stock.move'

    purchase_line_id = fields.Many2one('am_purchase.order.line', 'Purchase Order Line', ondelete='set null', index=True,
                                       readonly=True)
