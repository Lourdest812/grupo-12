# models/res_users.py
from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    property_ids = fields.One2many(
        comodel_name="estate.property",
        inverse_name="salesman_id",
        string="Propiedades",
    )

    property_count = fields.Integer(
        string="Propiedades",
        compute="_compute_property_count",
    )

    @api.depends('property_ids')
    def _compute_property_count(self):
        for user in self:
            user.property_count = len(user.property_ids)

    def action_open_user_properties(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Propiedades",
            "res_model": "estate.property",
            "view_mode": "list,form",
            "domain": [("salesman_id", "=", self.id)],
            "context": {"default_salesman_id": self.id},
        }
