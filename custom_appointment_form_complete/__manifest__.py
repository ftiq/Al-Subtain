{
    "name": "Custom Appointment Form: Service + File Upload",
    "version": "1.0",
    "category": "Website",
    "summary": "Enhances appointment form to include service selection and file upload, saved into calendar.event",
    "depends": ["website", "appointment", "calendar", "sale_management"],
   "data": [
    "views/appointment_extra_fields.xml",
    "views/website_appointment_form.xml",
    "views/calendar_event_form.xml"
    ],
    "installable": True,
    "application": False
}
