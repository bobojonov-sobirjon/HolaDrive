from django.conf import settings
from django.db import models


class SavedCard(models.Model):
    """
    Stripe PaymentMethod rows saved for a user (rider or driver).
    Same physical person uses CustomUser; holder_role separates rider vs driver card lists.
    """

    class HolderRole(models.TextChoices):
        RIDER = 'rider', 'Rider'
        DRIVER = 'driver', 'Driver'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_cards',
    )
    holder_role = models.CharField(
        max_length=20,
        choices=HolderRole.choices,
        default=HolderRole.RIDER,
        db_index=True,
        help_text='Rider: pay for trips. Driver: optional cards (e.g. payouts) — product-specific.',
    )
    stripe_payment_method_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Stripe PaymentMethod id (pm_…).',
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        help_text='Stripe Customer id (cus_…) this PM is attached to.',
    )
    brand = models.CharField(max_length=32, blank=True)
    last4 = models.CharField(max_length=4, blank=True)
    exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    funding = models.CharField(
        max_length=20,
        blank=True,
        help_text='Stripe card funding: credit, debit, prepaid, unknown.',
    )
    nickname = models.CharField(
        max_length=64,
        blank=True,
        help_text='Optional label shown in the app.',
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True,
        help_text='False when detached in Stripe or removed in app.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Saved card'
        verbose_name_plural = 'Saved cards'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'holder_role'],
                condition=models.Q(is_default=True),
                name='savedcard_unique_default_per_user_holder_role',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'holder_role', 'is_active']),
        ]

    def __str__(self):
        role = self.get_holder_role_display()
        tail = f' …{self.last4}' if self.last4 else ''
        return f'{self.user_id} ({role}){tail}'
