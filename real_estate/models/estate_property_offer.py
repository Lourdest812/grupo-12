# real_estate/models/estate_property_offer.py
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Oferta sobre propiedad"
    _order = "price desc, id desc"

    # ------------------ Campos ------------------
    price = fields.Float(string="Precio", required=True)

    status = fields.Selection(
        selection=[("accepted", "Aceptada"), ("refused", "Rechazada")],
        string="Estado",
        default=False,
        copy=False,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Ofertante",
        required=True,
        index=True,
        ondelete="restrict",
    )

    property_id = fields.Many2one(
        comodel_name="estate.property",
        string="Propiedad",
        required=True,
        index=True,
        ondelete="cascade",
    )

    validity = fields.Integer(string="Validez (días)", default=7)

    date_deadline = fields.Date(
        string="Fecha límite",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True,
    )

    # Solo para mostrar el tipo en listas
    property_type_id = fields.Many2one(
        comodel_name="estate.property.type",
        string="Tipo de propiedad",
        related="property_id.property_type_id",
        store=True,
        readonly=True,
    )

    # ------------------ Compute / Inverse ------------------
    @api.depends("validity", "create_date")
    def _compute_date_deadline(self):
        """fecha límite = (create_date o hoy) + validity"""
        today = fields.Date.context_today(self)
        for rec in self:
            base = (rec.create_date and fields.Date.to_date(rec.create_date)) or today
            rec.date_deadline = base + timedelta(days=(rec.validity or 0))

    def _inverse_date_deadline(self):
        """Si cambian la fecha límite, recalcular validity en días."""
        today = fields.Date.context_today(self)
        for rec in self:
            base = (rec.create_date and fields.Date.to_date(rec.create_date)) or today
            if rec.date_deadline:
                rec.validity = (rec.date_deadline - base).days

    # ------------------ Punto 23: reglas en create ------------------
    @api.model
    def create(self, vals):
        """
        a) El precio debe ser MAYOR a la mejor oferta existente de la propiedad.
        b) Solo permitir crear si la propiedad está en 'new' u 'offer_received'.
        c) Tras crear, poner la propiedad en 'offer_received'.
        """
        # Permitir create([]) por si viene en batch
        if isinstance(vals, list):
            recs = self.browse()
            for v in vals:
                recs |= self.create(v)
            return recs

        prop_id = vals.get("property_id") or self.env.context.get("default_property_id")
        if not prop_id:
            raise UserError(_("Debes indicar la propiedad de la oferta."))

        prop = self.env["estate.property"].browse(prop_id)
        if not prop.exists():
            raise UserError(_("La propiedad indicada no existe."))

        # (b) estado permitido
        if prop.state not in ("new", "offer_received"):
            raise UserError(
                _(
                    "Solo puedes crear ofertas cuando la propiedad está en "
                    "'Nuevo' u 'Oferta recibida'. Estado actual: %s"
                )
                % dict(prop._fields["state"].selection).get(prop.state, prop.state)
            )

        # (a) precio mayor a la mejor oferta actual
        new_price = float(vals.get("price") or 0.0)
        best = max(prop.offer_ids.mapped("price") or [0.0])
        if new_price <= best:
            raise UserError(
                _("El precio ofertado (%.2f) debe ser MAYOR a la mejor oferta actual (%.2f).")
                % (new_price, best)
            )

        # Crear y (c) asegurar estado
        rec = super().create(vals)
        if rec.property_id.state == "new":
            rec.property_id.state = "offer_received"
        return rec

    # ------------------ Acciones ------------------
    def action_accept_offer(self):
        """
        Marcar aceptada, setear precio de venta y comprador,
        mover estado a 'offer_accepted' y rechazar el resto.
        """
        for rec in self:
            rec.status = "accepted"
            prop = rec.property_id
            prop.selling_price = rec.price
            prop.buyer_id = rec.partner_id
            prop.state = "offer_accepted"
            # Rechazar otras ofertas de la misma propiedad
            (prop.offer_ids - rec).write({"status": "refused"})
        return True

    def action_refuse_offer(self):
        for rec in self:
            rec.status = "refused"
        return True
