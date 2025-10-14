from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError
from odoo.tools import float_round
import random


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Propiedades"

    name = fields.Char(string="Title", required=True)
    description = fields.Text(string="Descripcion")
    postcode = fields.Char(string="Codigo Postal")

    property_type_id = fields.Many2one(
        "estate.property.type",
        string="Tipo Propiedad",
        ondelete="set null",
        index=True,
    )

    buyer_id = fields.Many2one(
        "res.partner",
        string="Comprador",
        ondelete="set null",
        index=True,
    )

    salesman_id = fields.Many2one(
        "res.users",
        string="Vendedor",
        default=lambda self: self.env.user,
        copy=False,
        ondelete="set null",
        index=True,
    )

    tag_ids = fields.Many2many(
        comodel_name="estate.property.tag",
        relation="estate_property_tag_rel",
        column1="property_id",
        column2="tag_id",
        string="Etiquetas",
    )

    offer_ids = fields.One2many(
        comodel_name="estate.property.offer",
        inverse_name="property_id",
        string="Ofertas",
    )

    # --- Personas que ofertaron (computado y almacenado)
    offer_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Personas que ofertaron",
        compute="_compute_offer_partner_ids",
        store=True,
        readonly=True,
    )

    @api.depends('offer_ids.partner_id')
    def _compute_offer_partner_ids(self):
        for rec in self:
            partners = rec.offer_ids.mapped('partner_id')
            rec.offer_partner_ids = [(6, 0, partners.ids)]

    date_availability = fields.Date(
        string="Fecha de disponibilidad",
        default=lambda self: fields.Date.today() + timedelta(days=90),
        copy=False,
    )

    expected_price = fields.Float(string="Precio esperado")
    selling_price = fields.Float(string="Precio de venta", copy=False)

    bedrooms = fields.Integer(string="Habitaciones", default=2)
    living_area = fields.Integer(string="Superficie Cubierta")
    facade = fields.Integer(string="Fachadas")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Jardin")
    garden_orientation = fields.Selection(
        selection=[("north", "Norte"), ("south", "Sur"), ("east", "Este"), ("west", "Oeste")],
        default="north",
        string="Orientacion del jardin",
    )
    garden_area = fields.Integer(string="Superficie del jardin")

    state = fields.Selection(
        selection=[
            ("new", "Nuevo"),
            ("offer_received", "Oferta recibida"),
            ("offer_accepted", "Oferta aceptada"),
            ("sold", "Vendido"),
            ("canceled", "Cancelado"),
        ],
        default="new",
        copy=False,
        string="Estado",
        required=True,
    )

    # ---------------- Acciones varias ----------------
    def action_sold(self):
        for rec in self:
            if rec.state == 'canceled':
                raise UserError("No se puede marcar como vendida una propiedad cancelada")
            rec.state = 'sold'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'sold':
                raise UserError("No se puede cancelar una propiedad vendida")
            rec.state = 'canceled'

    total_area = fields.Float(
        string='Superficie total',
        compute='_compute_total_area',
        store=True
    )

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = (record.living_area or 0) + (record.garden_area or 0)

    best_offer = fields.Float(
        string='Mejor oferta',
        compute='_compute_best_offer',
        store=True
    )

    @api.depends('offer_ids.price')
    def _compute_best_offer(self):
        for rec in self:
            offers = rec.offer_ids.mapped('price')
            rec.best_offer = max(offers) if offers else 0

    @api.onchange('garden')
    def _onchange_garden(self):
        for record in self:
            record.garden_area = 10 if record.garden else 0

    @api.onchange('expected_price')
    def _onchange_expected_price(self):
        for record in self:
            if record.expected_price and record.expected_price < 10000:
                return {
                    'warning': {
                        'title': "Precio bajo",
                        'message': "El precio esperado es menor a 10.000. Por favor, verifica si ingresaste el valor correctamente.",
                    }
                }

    # -------------- Punto 20: Generar oferta automática --------------
    def action_generate_auto_offer(self):
        for rec in self:
            if not rec.expected_price:
                raise UserError("Definí el 'Precio esperado' antes de generar ofertas.")

            candidates = self.env['res.partner'].search([
                ('active', '=', True),
                ('id', 'not in', rec.offer_partner_ids.ids),
            ])
            if not candidates:
                raise UserError("No hay contactos activos disponibles que no hayan ofertado esta propiedad.")

            partner = random.choice(candidates)
            factor = 1 + random.uniform(-0.30, 0.30)   # +/- 30%
            price = float_round(rec.expected_price * factor, precision_digits=2)

            self.env['estate.property.offer'].create({
                'price': price,
                'partner_id': partner.id,
                'property_id': rec.id,
            })

            if rec.state == 'new':
                rec.state = 'offer_received'
        return True

    # -------------- Punto 21: botones de etiquetas --------------
    def action_clear_tags(self):
        """Sacar etiquetas: desvincula todas las etiquetas actuales"""
        for rec in self:
            rec.write({'tag_ids': [(6, 0, [])]})
        return True

    def action_load_all_tags(self):
        """Cargar todas las etiquetas existentes en el sistema"""
        all_tag_ids = self.env['estate.property.tag'].search([]).ids
        for rec in self:
            rec.write({'tag_ids': [(6, 0, all_tag_ids)]})
        return True

    def action_tag_new(self):
        """
        'A estrenar': crea la etiqueta si no existe y la vincula
        (si existe, solo vincular).
        """
        Tag = self.env['estate.property.tag']
        tag = Tag.search([('name', '=', 'A estrenar')], limit=1)
        if not tag:
            tag = Tag.create({'name': 'A estrenar'})
        for rec in self:
            rec.write({'tag_ids': [(4, tag.id)]})
        return True

    # -------------- Punto 22: permitir borrar solo 'new' o 'canceled' --------------
    @api.ondelete(at_uninstall=False)
    def _unlink_if_new_or_cancelled(self):
        """
        Solo permite borrar propiedades cuando el estado es 'new' o 'canceled'.
        Si alguna no cumple, se bloquea el borrado con un error.
        """
        invalid = self.filtered(lambda r: r.state not in ('new', 'canceled'))
        if invalid:
            names = ", ".join(invalid.mapped('name'))
            raise UserError(
                "Solo se pueden borrar propiedades en estado 'Nuevo' o 'Cancelado'. "
                f"No cumplen: {names}"
            )
        # Si no hay inválidas, Odoo continúa con unlink() normalmente.
