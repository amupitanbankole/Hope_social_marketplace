from django.contrib import admin
from .models import Service, AccountItem, Order, Transaction, Referral, SupportTicket, TicketReply, Provider, PaymentSetting

@admin.register(PaymentSetting)
class PaymentSettingAdmin(admin.ModelAdmin):
    list_display = ['id', 'bank_name', 'account_name', 'account_number', 'flutterwave_public_key', 'updated_at']

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'api_url', 'margin_percentage', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'api_url']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing_type', 'platform', 'category', 'name', 'rate_per_1k', 'provider', 'provider_service_id', 'is_active']
    list_filter = ['listing_type', 'platform', 'category', 'provider', 'is_active']
    search_fields = ['name', 'platform', 'category', 'provider_service_id']

@admin.register(AccountItem)
class AccountItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'platform', 'name', 'year', 'price', 'is_in_stock']
    list_filter = ['platform', 'year', 'is_in_stock']
    search_fields = ['name', 'platform']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'service_name', 'quantity', 'total_amount', 'status', 'provider_order_id', 'date']
    list_filter = ['status', 'date']
    search_fields = ['id', 'user__username', 'service_name', 'provider_order_id']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'transaction_type', 'amount', 'status', 'method', 'reference', 'date']
    list_filter = ['transaction_type', 'status', 'method']
    search_fields = ['reference', 'user__username']

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['id', 'referrer', 'referred_user', 'total_commission_earned', 'date']

class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 1

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'subject', 'category', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority', 'category']
    inlines = [TicketReplyInline]
