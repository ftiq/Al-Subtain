from odoo import models, fields

class DocumentsRequest(models.TransientModel):
    _inherit = 'documents.request'

    book_type = fields.Selection([
        ('change',       'طلب تغيير'),
        ('school_reg',   'طلب تسجيل مدرسة'),
        ('referral',     'طلب إحالة'),
        ('aid_disburse', 'طلب صرف إعانة'),
        ('purchase',     'طلب شراء'),
        ('secondment',   'طلب تفرغ'),
    ], string="نوع الكتاب", required=True)

    importance = fields.Selection([
        ('low',    'منخفض'),
        ('normal', 'عادي'),
        ('high',   'عالي'),
    ], string="أهمية الكتاب")

    book_dest_ids = fields.Many2many(
        'res.partner',
        'documents_request_dest_rel',
        'request_id', 'partner_id',
        string="جهة توجيه الكتاب",
        help="يمكن ترتيب الجهات بالسحب والإفلات",
    )
    to_partner_ids = fields.Many2many(
        'res.partner',
        'documents_request_to_rel',
        'request_id', 'partner_id',
        string="إلى",
    )

    subject = fields.Char(string="موضوع الكتاب")
    summary = fields.Text(string="ملخص الكتاب")
    content = fields.Html(string="محتوى الكتاب")
