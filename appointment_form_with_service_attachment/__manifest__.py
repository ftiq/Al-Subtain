{
    "name": "Appointment Form: Service + Attachment",
    "version": "1.0",
    "category": "Website",
    "summary": "Adds service selection and file upload to the default Odoo appointment form (calendar.event)",
    "depends": ["website", "appointment", "calendar", "sale_management"],
    "data": [
        "views/form_override.xml",
        "views/calendar_event_form.xml"
    ],
    "installable": True,
    "application": False
}
