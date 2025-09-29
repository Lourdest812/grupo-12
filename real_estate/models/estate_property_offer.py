from datetime import timedelta
from odoo import models, fields,api


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Oferta sobre propiedad"

    price = fields.Float(
        string="Precio",
        required=True,
    )

    status = fields.Selection(
        selection=[
            ("accepted", "Aceptada"),
            ("refused", "Rechazada"),
        ],
        string="Estado",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Ofertante",
        required=True
    )

    property_id = fields.Many2one(
        comodel_name="estate.property",
        string="Propiedad",
        required=True
    )
    validity = fields.Integer(
        string="Validez (días)",
        default=7
    )
    date_deadline=fields.Date(
        string="Fecha límite",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True
    )
    # Campo relacionado
    property_type_id = fields.Many2one(
        comodel_name="estate.property.type",
        string="Tipo de propiedad",
        related="property_id.property_type_id",
        store=True
    )

    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                # Solo se calcula si el usuario no puso date_deadline manualmente
                if not record.date_deadline:
                    record.date_deadline = record.create_date.date() + timedelta(days=record.validity)

    def _inverse_date_deadline(self):
        for record in self:
            if record.create_date and record.date_deadline:
                record.validity = (record.date_deadline - record.create_date.date()).days

    def action_accept_offer(self):
        for offer in self:
            offer.status = 'accepted'
            offer.property_id.selling_price = offer.price
            offer.property_id.buyer_id = offer.partner_id
            offer.property_id.state = 'offer_accepted'

        # Rechazar otras ofertas
        (offer.property_id.offer_ids - offer).write({'status': 'refused'})
