# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def report_action(self, docids, data=None, config=True):
        """Call super then يسجل رسالة في شاتر استلام المخزون"""
        action = super(IrActionsReport, self).report_action(docids, data=data, config=config)
        try:

            ctx = self.env.context
            active_model = ctx.get('active_model')
            active_ids_ctx = ctx.get('active_ids') or []

            is_picking_model = self.model == 'stock.picking' or active_model == 'stock.picking'

            if not is_picking_model:
                return action


            record_ids = []
            if docids:
                if isinstance(docids, models.Model):
                    record_ids = docids.ids
                elif isinstance(docids, int):
                    record_ids = [docids]
                elif isinstance(docids, (list, tuple)):
                    record_ids = list(docids)


            for rid in active_ids_ctx:
                if rid not in record_ids:
                    record_ids.append(rid)

            if record_ids:
                pickings = self.env['stock.picking'].browse(record_ids)

                report_name = self.name or self.report_name or _('Unknown Report')
                date_str = fields.Datetime.context_timestamp(self.env.user, fields.Datetime.now()).strftime('%Y-%m-%d %H:%M:%S')


                body_html = (
                    '<div class="alert alert-warning o_print_log_alert" '
                    'style="margin:0;border-right:4px solid #ffa726;direction:rtl;text-align:right;">'
                    '<i class="fa fa-print" style="margin-left:4px;"></i> '
                    '<strong>تم طباعة تقرير %(rep)s</strong><br/>'
                    '<span style="font-size:12px;">بتاريخ %(date)s</span>'
                    '</div>'
                ) % {
                    'rep': report_name,
                    'date': date_str,
                }
                body = Markup(body_html)
                for picking in pickings:
                    try:
                        picking.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')
                    except Exception:
                        _logger.exception('Unable to post print message on picking %s', picking.id)
        except Exception:
            _logger.exception('Error while posting print log note.')
        return action 