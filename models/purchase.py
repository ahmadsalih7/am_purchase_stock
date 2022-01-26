# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.am_purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseOrder(models.Model):
    _inherit = 'am_purchase.order'

    @api.model
    def _get_picking_type(self):
        return self.env['am_stock.picking.type'].search([('code', '=', 'incoming')], limit=1)

    picking_ids = fields.Many2many('am_stock.picking', string='Receptions', copy=False, store=True)
    picking_type_id = fields.Many2one('am_stock.picking.type', 'Deliver To', states=Purchase.READONLY_STATES,
                                      required=True, default=_get_picking_type,
                                      domain="['|', ('warehouse_id', '=', False),"
                                             "('warehouse_id.company_id', '=', company_id)]",
                                      help="This will determine operation type of incoming shipment")

    def button_approve(self):
        result = super(PurchaseOrder, self).button_approve()
        self._create_picking()
        return result

    def _create_picking(self):
        StockPicking = self.env['am_stock.picking']
        for order in self:
            if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                if not pickings:
                    res = order._prepare_picking()
                    picking = StockPicking.create(res)
                else:
                    picking = pickings[0]
                move = order.order_line._create_stock_moves(picking)
                picking.write({
                    'move_ids': [(4, move.id, 0)],
                })
                move._action_confirm()
                move._action_assign()

    @api.model
    def _prepare_picking(self):
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'company_id': self.company_id.id,
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'am_purchase.order.line'

    move_ids = fields.One2many('am_stock.move', 'purchase_line_id', string='Reservation', readonly=True,
                               ondelete='set null', copy=False)

    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res
        res = {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_quantity': self.product_qty,
            'create_date': self.order_id.date_order,
            'picking_id': picking.id,
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'picking_type_id': self.order_id.picking_type_id.id,
            'origin': self.order_id.name,
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
        }
        return res

    def _create_stock_moves(self, picking):
        values = []
        for line in self:
            values = line._prepare_stock_moves(picking)
            return self.env['am_stock.move'].create(values)
