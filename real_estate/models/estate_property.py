from odoo import fields, models


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Propiedades"

    name = fields.Char(string="Title", required=True)
    description = fields.Text(string="Descripcion")
    postcode=fields.Char(string="Codigo Postal")
    date_availability = fields.Date(string="Fecha de disponibilidad", default=fields.Date.today)
    expected_price = fields.Float(string="Precio esperado")
    sellind_price = fields.Float(string="Precio de venta")
    bedrooms = fields.Integer(string="Habitaciones",default=2)
    living_area = fields.Integer(string="Superficie Cubierta")
    Facade = fields.Integer(string="Fachadas")
    garage=fields.Boolean(string="Garage")
    garden=fields.Boolean(string="Jardin")
    garden_orientation=fields.Selection(selection=[('north','Norte'),('south','Sur'),('east','Este'),('west','Oeste')],default="north",string="Orientacion del jardin")
    garden_area=fields.Integer(string="Superficie del jardin")
