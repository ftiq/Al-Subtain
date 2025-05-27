{
    "name": "Website Appointment Enhanced (Override Default)",
    "version": "1.2",
    "category": "Website",
    "summary": "Extends Odoo default appointment form to support service selection and file upload",
    "depends": ["website", "calendar", "sale_management", "appointment"],
    "data": [
        "views/appointment_form_override.xml",
        "views/calendar_event_form.xml"
    ],
    "installable": True,
    "application": True
}
