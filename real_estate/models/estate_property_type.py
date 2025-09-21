from odoo import models, fields


class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Tipo de Propiedad"
    _order = "name"

    name = fields.Char(string="Nombre", required=True, index=True)