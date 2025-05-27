{
    "name": "Safe Appointment Form Extension",
    "version": "1.0",
    "category": "Website",
    "summary": "Add service & file upload to appointment form (no nested inherit)",
    "depends": ["website", "appointment", "calendar", "sale_management"],
    "data": [
        "views/appointment_fields.xml",
        "views/appointment_form.xml",
        "views/calendar_event_form.xml"
    ],
    "installable": True,
    "application": False
}
