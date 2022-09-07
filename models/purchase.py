# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.am_purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseOrder(models.Model):
    _inherit = 'am_purchase.order'

    @api.model
    def _get_picking_type(self):
        """ As this is a purchase operation then the picking type must be incoming (Delivery) """
        return self.env['am_stock.picking.type'].search([('code', '=', 'incoming')], limit=1)

    picking_ids = fields.Many2many('am_stock.picking', string='Receptions', copy=False, store=True)
    picking_type_id = fields.Many2one('am_stock.picking.type', 'Deliver To', states=Purchase.READONLY_STATES,
                                      required=True, default=_get_picking_type,
                                      domain="['|', ('warehouse_id', '=', False),"
                                             "('warehouse_id.company_id', '=', company_id)]",
                                      help="This will determine operation type of incoming shipment")
    picking_count = fields.Integer(compute='_compute_picking', string='Picking count', default=0, store=True)

    def button_approve(self):
        """ Add additional functionality to create stock picking after approval """
        # Call the super approve function
        result = super(PurchaseOrder, self).button_approve()
        # Call create picking funtion
        self._create_picking()
        return result

    def _create_picking(self):
        """ Create picking from the purchase order"""
        StockPicking = self.env['am_stock.picking']
        # loop over the orders
        for order in self:
            # Check the products type
            if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
                # Check if any stock picking are already generated and not done
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                # if No picking are there then create
                if not pickings:
                    # Populate the picking object
                    res = order._prepare_picking()
                    # Create picking object using the populated object
                    picking = StockPicking.create(res)
                    # Append the created object to the order
                    order.write({'picking_ids': [(6, False, [picking.id])]})
                else:
                    picking = pickings[0]
                # then create the stock move using the order line (products)
                moves = order.order_line._create_stock_moves(picking)
                for move in moves:
                    picking.write({
                        'move_lines': [(4, move.id, 0)],
                    })
                    move._action_confirm()
                    move._action_assign()
        return True

    @api.model
    def _prepare_picking(self):
        """ Use purchase order data to populate picking object"""
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            # Let the origin be the purchase order name (Seq.)
            'origin': self.name,
            'company_id': self.company_id.id,
        }

    @api.depends('order_line.move_ids.picking_id')
    def _compute_picking(self):
        for order in self:
            order.picking_count = len(order.order_line.mapped('move_ids.picking_id'))

    def action_view_picking(self):
        result = self.env.ref('am_stock.action_overview').read()[0]
        pick_ids = self.mapped('picking_ids')
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('am_stock.view_am_stock_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result


class PurchaseOrderLine(models.Model):
    """ Add stock related functionality to Purchase module """
    _inherit = 'am_purchase.order.line'

    # Creating Stock move based on order lines.
    move_ids = fields.One2many('am_stock.move', 'purchase_line_id', string='Reservation', readonly=True,
                               ondelete='set null', copy=False)

    def _prepare_stock_moves(self, picking):
        """ Populate stock move object with purchase order line's data """
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
            values.append(line._prepare_stock_moves(picking))
        return self.env['am_stock.move'].create(values)
