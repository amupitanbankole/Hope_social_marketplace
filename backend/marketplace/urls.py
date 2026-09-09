from django.urls import path
from .views import (
    ServiceListView, ServiceDetailView, AccountItemListView, AccountItemDetailView, OrderListCreateView,
    TransactionListView, WalletDepositView, FlutterwaveVerifyView, PaymentConfigView, DashboardStatsView,
    ReferralListView, SupportTicketListCreateView, TicketReplyCreateView,
    AdminOverviewView, AdminUserListView, AdminUserBlockToggleView,
    AdminPendingDepositsView, AdminConfirmDepositView, NotificationListView,
    AdminSupportTicketListView, AdminTicketReplyView, AdminOrdersListView, ProviderListView,
    MarketreumCatalogSyncView,
)

urlpatterns = [
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('services/', ServiceListView.as_view(), name='service-list'),
    path('services/<int:service_id>/', ServiceDetailView.as_view(), name='service-detail'),
    path('accounts/', AccountItemListView.as_view(), name='account-list'),
    path('accounts/<int:account_id>/', AccountItemDetailView.as_view(), name='account-detail'),
    path('orders/', OrderListCreateView.as_view(), name='order-list-create'),
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('wallet/deposit/', WalletDepositView.as_view(), name='wallet-deposit'),
    path('wallet/verify-flutterwave/', FlutterwaveVerifyView.as_view(), name='wallet-verify-flutterwave'),
    path('payment-config/', PaymentConfigView.as_view(), name='payment-config'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),

    path('referrals/', ReferralListView.as_view(), name='referral-list'),
    path('support/tickets/', SupportTicketListCreateView.as_view(), name='ticket-list-create'),
    path('support/tickets/<int:ticket_id>/reply/', TicketReplyCreateView.as_view(), name='ticket-reply-create'),

    # Admin routes
    path('admin/overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/toggle-block/', AdminUserBlockToggleView.as_view(), name='admin-user-toggle-block'),
    path('admin/deposits/', AdminPendingDepositsView.as_view(), name='admin-deposits'),
    path('admin/deposits/<int:deposit_id>/confirm/', AdminConfirmDepositView.as_view(), name='admin-confirm-deposit'),
    path('admin/support/tickets/', AdminSupportTicketListView.as_view(), name='admin-ticket-list'),
    path('admin/support/tickets/<int:ticket_id>/reply/', AdminTicketReplyView.as_view(), name='admin-ticket-reply'),
    path('admin/orders/', AdminOrdersListView.as_view(), name='admin-orders-list'),
    path('admin/orders/<int:order_id>/approve/', AdminOrdersListView.as_view(), name='admin-order-approve'),
    path('admin/providers/', ProviderListView.as_view(), name='admin-providers'),

    # Marketreum catalog integration
    path('admin/marketreum/sync/', MarketreumCatalogSyncView.as_view(), name='marketreum-sync'),
]
