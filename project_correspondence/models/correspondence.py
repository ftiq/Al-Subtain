from odoo import models, fields, api

class ProjectCorrespondence(models.Model):
    _name = 'project.correspondence'
    _description = 'Project Correspondence'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ('internal', 'صادر داخلي'),
        ('external', 'صادر خارجي'),
        ('tech', 'صادر فني'),
        ('incoming', 'وارد'),
    ]
    TYPE_SELECTION = [
        ('change', 'طلب - تغيير'),
        ('school', 'طلب - تسجيل مدرسة'),
        ('referral', 'طلب - إحالة'),
        ('aid', 'طلب - صرف إعانة'),
        ('purchase', 'طلب - شراء'),
        ('secondment', 'طلب - تفرغ'),
    ]
    PRIORITY_SELECTION = [
        ('normal', 'اعتيادي'),
        ('urgent', 'عاجل'),
        ('very_urgent', 'عاجل جداً'),
        ('secret', 'سري وشخصي'),
    ]

    name = fields.Char(string='رقم الكتاب', required=True, copy=False, readonly=True, default='New')
    state = fields.Selection(STATE_SELECTION, string='نوع الكتاب', required=True, default='internal', tracking=True)
    type = fields.Selection(TYPE_SELECTION, string='نوع الطلب', required=True)
    priority = fields.Selection(PRIORITY_SELECTION, string='أهمية الكتاب')
    department_id = fields.Many2one('hr.department', string='جهة التوجيه')
    user_to_id = fields.Many2one('res.users', string='إلى')
    subject = fields.Char(string='موضوع الكتاب')
    summary = fields.Text(string='ملخص الكتاب')
    body = fields.Html(string='محتوى الكتاب')
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id', string='المرفقات',
        domain=[('res_model', '=', 'project.correspondence')]
    )
    archive_status = fields.Selection([
        ('pending', 'قيد الأرشفة'),
        ('archived', 'مؤرشف'),
        ('exported', 'مصدَّر')
    ], string='حالة الأارشفة', default='pending', tracking=True)
    archive_ref = fields.Char(string='مرجع الأرشيف')
    archive_date = fields.Datetime(string='تاريخ الأارشفة')
    log_ids = fields.One2many('project.correspondence.log', 'correspondence_id', string='سجل التغيير')

    @api.model
    def create(self, vals):
        seq_code = {
            'internal': 'project.correspondence.out_int',
            'external': 'project.correspondence.out_ext',
            'tech': 'project.correspondence.tech',
            'incoming': 'project.correspondence.in',
        }.get(vals.get('state'))
        if seq_code:
            vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or 'New'
        return super().create(vals)

    def action_change_state(self, new_state):
        for rec in self:
            old = rec.state
            rec.state = new_state
            rec.log_ids = [(0, 0, {
                'from_state': old,
                'to_state': new_state,
                'user_id': self.env.uid,
            })]
        return True

    def action_submit(self):
        return self.action_change_state('external')

    def action_archive(self):
        for rec in self:
            rec.archive_status = 'archived'
            rec.archive_date = fields.Datetime.now()
        return True
