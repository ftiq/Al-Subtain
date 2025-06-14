from odoo import models, fields, api

class InternalMail(models.Model):
    _name = 'internal.mail'
    _description = 'Internal Correspondence'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='رقم صادر', readonly=True, copy=False)
    date = fields.Datetime(string='التاريخ', default=lambda self: fields.Datetime.now(), tracking=True)
    sender_id = fields.Many2one('res.users', string='المرسل', default=lambda self: self.env.user, readonly=True)
    recipient_ids = fields.Many2many('res.partner', string='المستلمون')
    attachment_ids = fields.Many2many('ir.attachment', string='المرفقات')
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('sent', 'مرسل'),
        ('approved', 'معتمد'),
        ('modified', 'معدل'),
    ], string='الحالة', default='draft', tracking=True)
    whatsapp_sent = fields.Boolean(string='أرسل عبر واتساب', default=False)
    email_sent = fields.Boolean(string='أرسل عبر إيميل', default=False)

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('internal.mail.seq')
        return super().create(vals)

    def action_send_email(self):
        template = self.env.ref('my_internal_mail.email_template_internal_mail')
        template.send_mail(self.id, force_send=True)
        self.write({'state': 'sent', 'email_sent': True})

    def action_send_whatsapp(self):
        for rec in self:
            msg = f"لديك مراسلة جديدة برقم {rec.name}"
            link = f"https://api.whatsapp.com/send?phone={{partner.phone}}&text={msg}"
        self.write({'state': 'sent', 'whatsapp_sent': True})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_modify(self):
        self.write({'state': 'modified'})
