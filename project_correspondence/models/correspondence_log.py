from odoo import models, fields

class ProjectCorrespondenceLog(models.Model):
    _name = 'project.correspondence.log'
    _description = 'Correspondence State Change Log'

    correspondence_id = fields.Many2one('project.correspondence', ondelete='cascade', string='Correspondence')
    from_state = fields.Char(string='من الحالة')
    to_state = fields.Char(string='إلى الحالة')
    user_id = fields.Many2one('res.users', string='المستخدم', readonly=True)
    date = fields.Datetime(string='التاريخ', default=fields.Datetime.now, readonly=True)
    note = fields.Text(string='ملاحظة')
