# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class EstateProperty(models.Model):
    _inherit = "estate.property"

    def action_sold(self):
        """
        Redefinición pedida en el punto 27:
        - Genera un borrador de factura (account.move) al marcar como vendida.
        - Reglas:
          a) partner_id = buyer_id de la propiedad
          b) move_type = 'out_invoice'
          c) 2 líneas (account.move.line):
             1) name = nombre de la propiedad, quantity = 1, price_unit = selling_price
             2) name = 'Gastos administrativos', quantity = 1, price_unit = 100
        """
        for rec in self:
            # mismas validaciones de negocio que en la acción original
            if rec.state == 'canceled':
                raise UserError("No se puede marcar como vendida una propiedad cancelada.")
            if not rec.buyer_id:
                raise UserError("Definí el comprador antes de marcar como vendida.")
            if not rec.selling_price or rec.selling_price <= 0:
                raise UserError("Definí un 'Precio de venta' mayor a 0 antes de marcar como vendida.")

            # Construcción de líneas usando comandos relacionales
            # Nota: en Odoo 15+ el campo correcto es 'invoice_line_ids' (NO 'line_ids').
            invoice_lines = [
                (0, 0, {
                    "name": rec.name or "Propiedad",
                    "quantity": 1,
                    "price_unit": rec.selling_price,
                }),
                (0, 0, {
                    "name": "Gastos administrativos",
                    "quantity": 1,
                    "price_unit": 100,
                }),
            ]

            move_vals = {
                "move_type": "out_invoice",          # (b)
                "partner_id": rec.buyer_id.id,       # (a)
                "invoice_line_ids": invoice_lines,   # (c)
                # Podés agregar journal_id si tu BD no tiene default:
                # "journal_id": self.env["account.move"].with_context(default_move_type="out_invoice")._get_default_journal().id,
            }

            self.env["account.move"].create(move_vals)

        # Finalmente, dejá que la acción original cambie el estado a 'sold'
        return super().action_sold()
