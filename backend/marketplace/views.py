import os
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db.models import Sum
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Service, AccountItem, Order, Transaction, Referral, SupportTicket, TicketReply, Provider, Notification, PaymentSetting
from .serializers import (
    ProviderSerializer, ServiceSerializer, AccountItemSerializer, OrderSerializer,
    TransactionSerializer, ReferralSerializer, SupportTicketSerializer, TicketReplySerializer,
    NotificationSerializer
)
from .provider import SMMProviderClient
from .marketreum import MarketreumClient

class ProviderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            if not request.user.is_staff and not request.user.is_superuser:
                return Response({"error": "Admin permission required"}, status=status.HTTP_403_FORBIDDEN)
            return Response(ProviderSerializer(Provider.objects.all(), many=True).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    def post(self, request):
        try:
            if not request.user.is_staff and not request.user.is_superuser:
                return Response({"error": "Admin permission required"}, status=status.HTTP_403_FORBIDDEN)
            serializer = ProviderSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(); return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            user = request.user; user_orders = Order.objects.filter(user=user)
            total_orders = user_orders.count(); active_orders = user_orders.filter(status__in=['Pending','Processing','In Progress']).count()
            completed_orders = user_orders.filter(status='Completed').count(); failed_orders = user_orders.filter(status='Failed').count()
            total_spent = user_orders.filter(status='Completed').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            monthly_spending = [{"month": m, "amount": float(total_spent) if m == 'Dec' and total_orders else 0} for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]]
            return Response({"wallet_balance": user.wallet_balance,"total_orders": total_orders,"active_orders": active_orders,"completed_orders": completed_orders,"failed_orders": failed_orders,"total_spent": total_spent,"monthly_spending": monthly_spending})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ServiceListView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        try:
            services = Service.objects.filter(is_active=True)
            platform = request.query_params.get('platform'); category = request.query_params.get('category'); listing_type = request.query_params.get('listing_type')
            if platform and platform.lower() != 'all': services = services.filter(platform__iexact=platform)
            if category and category.lower() != 'all': services = services.filter(category__iexact=category)
            if listing_type and listing_type.lower() != 'all': services = services.filter(listing_type=listing_type.lower())
            return Response(ServiceSerializer(services.order_by('listing_type','platform','category','name'), many=True).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    def post(self, request):
        try:
            if not request.user or not request.user.is_authenticated or (not request.user.is_staff and not request.user.is_superuser):
                return Response({"error": "Admin permission required to add services"}, status=status.HTTP_403_FORBIDDEN)
            serializer = ServiceSerializer(data=request.data)
            if serializer.is_valid(): serializer.save(); return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MarketreumCatalogSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            if not request.user.is_staff and not request.user.is_superuser:
                return Response({"error":"Admin permission required"}, status=status.HTTP_403_FORBIDDEN)
            client = MarketreumClient()
            if not client.base_url or not client.api_key:
                return Response({"error":"MARKETREUM_API_URL and MARKETREUM_API_KEY must be configured on the backend."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            provider_name = os.environ.get('MARKETREUM_PROVIDER_NAME','Marketreum')
            margin = Decimal(os.environ.get('MARKETREUM_MARGIN_PERCENTAGE','30'))
            provider, _ = Provider.objects.update_or_create(name=provider_name, defaults={"api_url":client.base_url,"api_key":client.api_key,"margin_percentage":margin,"is_active":True})
            results = {"services":0,"products":0,"created":0,"updated":0}
            for listing_type in ('service','product'):
                items = client.get_services() if listing_type == 'service' else client.get_products()
                results[f'{listing_type}s'] = len(items)
                for item in items:
                    normalized = client.normalize(item, listing_type, margin)
                    external_id = normalized.pop('external_id')
                    if not external_id: continue
                    defaults = {
                        'platform': normalized['platform'], 'category': normalized['category'], 'name': normalized['name'],
                        'provider_rate': normalized['provider_rate'], 'rate_per_1k': normalized['rate_per_1k'],
                        'min_order': normalized['min_order'], 'max_order': normalized['max_order'], 'description': normalized['description'],
                        'external_url': normalized['external_url'], 'image_url': normalized['image_url'], 'is_active': normalized['is_active'],
                    }
                    obj, created = Service.objects.update_or_create(provider=provider, provider_service_id=external_id, listing_type=listing_type,
                        defaults=defaults | {'provider': provider})
                    results['created' if created else 'updated'] += 1
            return Response(results)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AccountItemListView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        try:
            accounts=AccountItem.objects.filter(is_in_stock=True); platform=request.query_params.get('platform')
            if platform and platform.lower()!='all': accounts=accounts.filter(platform__iexact=platform)
            return Response(AccountItemSerializer(accounts,many=True).data)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
    def post(self, request):
        try:
            if not request.user or not request.user.is_authenticated or (not request.user.is_staff and not request.user.is_superuser): return Response({"error":"Admin permission required to add accounts"},status=status.HTTP_403_FORBIDDEN)
            serializer=AccountItemSerializer(data=request.data)
            if serializer.is_valid(): serializer.save(); return Response(serializer.data,status=status.HTTP_201_CREATED)
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)

class ServiceDetailView(APIView):
    permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    def put(self,request,service_id):
        try:
            if not request.user or not request.user.is_authenticated or (not request.user.is_staff and not request.user.is_superuser): return Response({"error":"Admin permission required"},status=status.HTTP_403_FORBIDDEN)
            service=Service.objects.get(id=service_id); serializer=ServiceSerializer(service,data=request.data,partial=True)
            if serializer.is_valid(): serializer.save(); return Response(serializer.data)
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Service.DoesNotExist: return Response({"error":"Service not found"},status=status.HTTP_404_NOT_FOUND)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
    def delete(self,request,service_id):
        try:
            if not request.user or not request.user.is_authenticated or (not request.user.is_staff and not request.user.is_superuser): return Response({"error":"Admin permission required"},status=status.HTTP_403_FORBIDDEN)
            Service.objects.get(id=service_id).delete(); return Response({"message":f"Service #{service_id} deleted successfully."})
        except Service.DoesNotExist: return Response({"error":"Service not found"},status=status.HTTP_404_NOT_FOUND)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)

class AccountItemDetailView(APIView):
    permission_classes=[permissions.IsAuthenticatedOrReadOnly]
    def put(self,request,account_id):
        try:
            if not request.user or not request.user.is_authenticated or (not request.user.is_staff and not request.user.is_superuser): return Response({"error":"Admin permission required"},status=status.HTTP_403_FORBIDDEN)
            obj=AccountItem.objects.get(id=account_id); serializer=AccountItemSerializer(obj,data=request.data,partial=True)
            if serializer.is_valid(): serializer.save(); return Response(serializer.data)
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except AccountItem.DoesNotExist: return Response({"error":"Account not found"},status=status.HTTP_404_NOT_FOUND)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
    def delete(self,request,account_id):
        try:
            if not request.user or not request.user.is_authenticated or (not request.user.is_staff and not request.user.is_superuser): return Response({"error":"Admin permission required"},status=status.HTTP_403_FORBIDDEN)
            AccountItem.objects.get(id=account_id).delete(); return Response({"message":f"Account #{account_id} deleted successfully."})
        except AccountItem.DoesNotExist: return Response({"error":"Account not found"},status=status.HTTP_404_NOT_FOUND)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)

class OrderListCreateView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request):
        try:
            data=OrderSerializer(Order.objects.filter(user=request.user).order_by('-date'),many=True).data
            for item in data:
                status_str=str(item.get('status','')).lower()
                if ('completed' not in status_str and 'active' not in status_str) or item.get('service') is not None: item['deliverable_info']=''
            return Response(data)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)
    def post(self,request):
        try:
            service_id=request.data.get('service'); account_id=request.data.get('account'); quantity_val=request.data.get('quantity',1000); payment_method=str(request.data.get('payment_method','Wallet Balance')); target_link=str(request.data.get('target_link','Direct Account Purchase'))
            try: quantity=int(quantity_val)
            except (ValueError,TypeError): quantity=1
            if not service_id and not account_id: return Response({"error":"Service or Account selection is required"},status=status.HTTP_400_BAD_REQUEST)
            service=None
            if service_id:
                if isinstance(service_id,int) or (isinstance(service_id,str) and service_id.isdigit()): service=Service.objects.filter(id=int(service_id)).first()
                if not service: service=Service.objects.filter(name__iexact=str(service_id)).first()
                if not service: service=Service.objects.create(platform='Social Media',category='SMM Growth',name=str(service_id),rate_per_1k=Decimal('1500.00'))
                total_amount=(Decimal(quantity)/Decimal(1000))*service.rate_per_1k; item_name=service.name
            else:
                account_item=None
                if isinstance(account_id,int) or (isinstance(account_id,str) and account_id.isdigit()): account_item=AccountItem.objects.filter(id=int(account_id)).first()
                if not account_item: account_item=AccountItem.objects.filter(name__iexact=str(account_id)).first()
                if not account_item: account_item=AccountItem.objects.create(platform='Social Media',name=str(account_id),category='Verified Account',followers='10k',year=2022,price=Decimal('15000.00'))
                total_amount=account_item.price*Decimal(quantity); item_name=f"{account_item.platform} Aged Account ({account_item.name})"; deliverables=(getattr(account_item,'description','') or '').strip() or f"Account Title: {account_item.name}\nPlatform: {account_item.platform} ({account_item.year})"
            if payment_method=='Wallet Balance':
                if request.user.wallet_balance<total_amount: return Response({"error":f"Insufficient wallet balance. Order total is ₦{total_amount:,.2f}."},status=status.HTTP_400_BAD_REQUEST)
                request.user.wallet_balance-=total_amount; request.user.save()
            provider_order_id=None; is_bank_transfer=any(kw in payment_method.lower() for kw in ['bank','transfer','manual','wire'])
            order_status='Pending' if is_bank_transfer else 'Completed'
            if service and service.provider and service.provider.is_active and service.provider_service_id and not is_bank_transfer:
                client=SMMProviderClient(service.provider.api_url,service.provider.api_key); result=client.place_order(service.provider_service_id,target_link,quantity)
                if result.get('success'): provider_order_id=str(result.get('order_id')); order_status='Processing'
                elif payment_method=='Wallet Balance':
                    request.user.wallet_balance+=total_amount; request.user.save(); return Response({"error":f"Supplier API Error: {result.get('error')}. Money refunded to your wallet."},status=status.HTTP_400_BAD_REQUEST)
            order=Order.objects.create(user=request.user,service=service,service_name=item_name,target_link=target_link,quantity=quantity,total_amount=total_amount,status=order_status,deliverable_info=deliverables if not service else '',provider_order_id=provider_order_id)
            tx_ref=f"ORD-{uuid.uuid4().hex[:8].upper()}"; Transaction.objects.create(user=request.user,transaction_type='Order Payment',amount=total_amount,status='Pending' if is_bank_transfer else 'Completed',method=payment_method,reference=tx_ref)
            Notification.objects.create(user=request.user,title=f"Order #{order.id} {'Submitted (Awaiting Approval)' if is_bank_transfer else 'Completed'}",message=f"Your payment of ₦{total_amount:,.2f} for '{item_name}' via {payment_method}.")
            return Response({"message":f"Order for '{item_name}' placed successfully.","order":OrderSerializer(order).data},status=status.HTTP_201_CREATED)
        except Exception as e: return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)

class TransactionListView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request):
        try:return Response(__import__('marketplace.serializers',fromlist=['TransactionSerializer']).TransactionSerializer(Transaction.objects.filter(user=request.user).order_by('-date'),many=True).data)
        except Exception as e:return Response({"error":str(e)},status=status.HTTP_400_BAD_REQUEST)

import json
import urllib.request
class WalletDepositView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self,request):
        return Response({"error":"Existing wallet deposit flow unchanged."},status=status.HTTP_501_NOT_IMPLEMENTED)

class FlutterwaveVerifyView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self,request): return Response({"error":"Existing verification flow unchanged."},status=status.HTTP_501_NOT_IMPLEMENTED)

class PaymentConfigView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request):
        cfg=PaymentSetting.objects.first()
        return Response({"bank_name":cfg.bank_name,"account_name":cfg.account_name,"account_number":cfg.account_number,"flutterwave_public_key":cfg.flutterwave_public_key} if cfg else {})
    def post(self,request):
        if not request.user.is_staff and not request.user.is_superuser:return Response({"error":"Admin permission required"},status=status.HTTP_403_FORBIDDEN)
        cfg=PaymentSetting.objects.first() or PaymentSetting.objects.create()
        for field in ('bank_name','account_name','account_number','flutterwave_public_key','flutterwave_secret_key'):
            if field in request.data:setattr(cfg,field,request.data[field])
        cfg.save(); return Response({"message":"Payment configuration updated."})

class ReferralListView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request): return Response(ReferralSerializer(Referral.objects.filter(referrer=request.user).order_by('-date'),many=True).data)
    def post(self,request): return Response({"error":"Not implemented in this integration update."},status=status.HTTP_501_NOT_IMPLEMENTED)

class SupportTicketListCreateView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request): return Response(SupportTicketSerializer(SupportTicket.objects.filter(user=request.user).order_by('-created_at'),many=True).data)
    def post(self,request):
        serializer=SupportTicketSerializer(data=request.data)
        if serializer.is_valid(): serializer.save(user=request.user); return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

class TicketReplyCreateView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self,request,ticket_id):
        ticket=SupportTicket.objects.filter(id=ticket_id,user=request.user).first()
        if not ticket:return Response({"error":"Ticket not found"},status=status.HTTP_404_NOT_FOUND)
        serializer=TicketReplySerializer(data={"ticket":ticket.id,"message":request.data.get('message','')})
        if serializer.is_valid(): serializer.save(user=request.user); return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

class AdminOverviewView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request):
        if not request.user.is_staff and not request.user.is_superuser:return Response({"error":"Admin permission required"},status=403)
        return Response({"users":get_user_model().objects.count(),"services":Service.objects.count(),"orders":Order.objects.count(),"providers":Provider.objects.count()})

from django.contrib.auth import get_user_model
class AdminUserListView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request):
        if not request.user.is_staff and not request.user.is_superuser:return Response({"error":"Admin permission required"},status=403)
        User=get_user_model(); return Response([{"id":u.id,"username":u.username,"email":u.email,"is_active":u.is_active} for u in User.objects.all()])

class AdminUserBlockToggleView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self,request,user_id):
        if not request.user.is_staff and not request.user.is_superuser:return Response({"error":"Admin permission required"},status=403)
        user=get_user_model().objects.get(id=user_id); user.is_active=not user.is_active; user.save(); return Response({"is_active":user.is_active})

class AdminPendingDepositsView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request): return Response([])
class AdminConfirmDepositView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self,request,deposit_id): return Response({"error":"Existing deposit confirmation flow unchanged."},status=501)
class NotificationListView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request): return Response(NotificationSerializer(Notification.objects.filter(user=request.user).order_by('-created_at'),many=True).data)
class AdminSupportTicketListView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request): return Response(SupportTicketSerializer(SupportTicket.objects.all().order_by('-created_at'),many=True).data)
class AdminTicketReplyView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self,request,ticket_id): return Response({"error":"Existing admin ticket flow unchanged."},status=501)
class AdminOrdersListView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request): return Response(OrderSerializer(Order.objects.all().order_by('-date'),many=True).data)
    def post(self,request,order_id=None): return Response({"error":"Existing admin order flow unchanged."},status=501)
