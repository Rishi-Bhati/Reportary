import json
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin

class HtmxMessageMiddleware(MiddlewareMixin):
    """
    Middleware that serializes Django messages to the 'HX-Trigger' header
    if the request is an HTMX request. This allows rendering Django messages
    as toast notifications dynamically for AJAX and partial page updates.
    """
    def process_response(self, request, response):
        if request.headers.get('HX-Request') == 'true' and not (300 <= response.status_code < 400):
            storage = messages.get_messages(request)
            django_messages = []
            for msg in storage:
                django_messages.append({
                    'text': msg.message,
                    'type': msg.tags if msg.tags else 'info'
                })
            
            if django_messages:
                hx_trigger = response.headers.get('HX-Trigger')
                try:
                    if hx_trigger:
                        trigger_data = json.loads(hx_trigger)
                    else:
                        trigger_data = {}
                except json.JSONDecodeError:
                    trigger_data = {hx_trigger: True} if hx_trigger else {}
                
                trigger_data['htmxMessages'] = django_messages
                response['HX-Trigger'] = json.dumps(trigger_data)
        
        return response
