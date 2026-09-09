from django.db import models
from django.conf import settings

class Provider(models.Model):
    name = models.CharField(max_length=100)
    api_url = models.URLField(help_text="Standard SMM Panel API v2 URL (e.g. https://provider.com/api/v2)")
    api_key = models.CharField(max_length=255)
    margin_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=30.00, help_text="Percentage markup added to provider prices")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.margin_percentage}% profit margin)"

class Service(models.Model):
    LISTING_TYPE_CHOICES = [
        ('service', 'Service'),
        ('product', 'Product'),
    ]

    provider = models.ForeignKey(Provider, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    provider_service_id = models.CharField(max_length=100, blank=True, null=True)
    provider_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    platform = models.CharField(max_length=50)
    category = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    rate_per_1k = models.DecimalField(max_digits=10, decimal_places=2)
    min_order = models.IntegerField(default=10)
    max_order = models.IntegerField(default=100000)
    description = models.TextField(blank=True)
    badge = models.CharField(max_length=50, blank=True, null=True)
    stock_count = models.IntegerField(default=1000)
    is_active = models.BooleanField(default=True)

    # External marketplace metadata. These fields keep the existing UI/order
    # structure intact while allowing Marketreum products and services to be
    # displayed alongside the current SMM catalog.
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES, default='service', db_index=True)
    external_url = models.URLField(max_length=500, blank=True, default='')
    image_url = models.URLField(max_length=1000, blank=True, default='')

    def __str__(self):
        return f"{self.platform} - {self.name}"

class AccountItem(models.Model):
    platform = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    followers = models.CharField(max_length=50)
    year = models.IntegerField(default=2022)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    country = models.CharField(max_length=50, default="USA")
    stock_count = models.IntegerField(default=10)
    is_in_stock = models.BooleanField(default=True)
    badge = models.CharField(max_length=50, blank=True, null=True)
    icon_name = models.CharField(max_length=50, default="Instagram")
    description = models.TextField(blank=True, default="", help_text="Login credentials, email, or account specs")

    def __str__(self):
        return f"{self.platform} ({self.year}) - {self.name}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Processing', 'Processing'),
        ('In Progress', 'In Progress'),
        ('Pending', 'Pending'),
        ('Failed', 'Failed'),
        ('Canceled', 'Canceled'),
        ('Partial', 'Partial'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    service_name = models.CharField(max_length=255, blank=True)
    target_link = models.CharField(max_length=500)
    quantity = models.IntegerField(default=1000)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    deliverable_info = models.TextField(blank=True, default="", help_text="Account credentials or download link delivered to buyer")

    provider_order_id = models.CharField(max_length=100, blank=True, null=True)
    start_count = models.IntegerField(default=0)
    remains = models.IntegerField(default=0)

    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('Deposit', 'Deposit'),
        ('Withdrawal', 'Withdrawal'),
        ('Order Payment', 'Order Payment'),
        ('Refund', 'Refund'),
    ]
    STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Pending', 'Pending'),
        ('Failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Completed')
    method = models.CharField(max_length=50, default='Flutterwave')
    reference = models.CharField(max_length=100, unique=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tx {self.reference} - ${self.amount}"

class Referral(models.Model):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_sent')
    referred_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referred_by')
    total_commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.username} -> {self.referred_user.username}"

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Answered', 'Answered'),
        ('Closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=100, default='General Inquiry')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject}"

class TicketReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_staff_reply = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply on #{self.ticket.id} by {self.user.username}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for @{self.user.username}: {self.title}"

class PaymentSetting(models.Model):
    bank_name = models.CharField(max_length=100, default="Moniepoint / GTBank")
    account_name = models.CharField(max_length=100, default="HopeSocial Ltd")
    account_number = models.CharField(max_length=50, default="2034829102")
    flutterwave_public_key = models.CharField(max_length=255, default="FLWPUBK_TEST-demo-key", blank=True)
    flutterwave_secret_key = models.CharField(max_length=255, default="", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment Settings ({self.bank_name} - {self.account_number})"
