import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        secret = (getattr(settings, 'STRIPE_WEBHOOK_SECRET', '') or '').strip()
        if not secret:
            logger.warning('Stripe webhook received but STRIPE_WEBHOOK_SECRET is not set')
            return HttpResponse(status=503)

        signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        try:
            event = stripe.Webhook.construct_event(
                payload=request.body,
                sig_header=signature,
                secret=secret,
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            logger.warning('Stripe webhook signature verification failed')
            return HttpResponse(status=400)

        event_type = event.get('type')
        logger.info('Stripe webhook accepted type=%s id=%s', event_type, event.get('id'))
        return HttpResponse(status=200)
