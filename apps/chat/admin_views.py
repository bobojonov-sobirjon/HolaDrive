from django.contrib import admin
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import os
from datetime import datetime
import uuid

from .models import Conversation, Message
from .utils import get_support_user, get_file_type_from_extension


@staff_member_required
def chat_interface(request, conversation_id):
    """
    Chat interface for admin panel
    """
    from django.conf import settings
    conversation = get_object_or_404(Conversation, id=conversation_id)
    support_user = get_support_user()
    
    messages = Message.objects.filter(conversation=conversation).select_related('sender').order_by('created_at')
    
    context = {
        'conversation': conversation,
        'messages': messages,
        'support_user': support_user,
        'conversation_id': conversation_id,
        'opts': Conversation._meta,
        'has_view_permission': True,
        'has_change_permission': True,
        'websocket_url': getattr(settings, 'WEBSOCKET_URL', f"{request.get_host()}"),
    }
    
    return render(request, 'admin/chat/chat_interface.html', context)


@staff_member_required
@csrf_exempt
def send_message_api(request, conversation_id):
    """
    API endpoint for sending messages from admin panel
    Supports both text messages and file uploads
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        support_user = get_support_user()
        
        if request.user != support_user:
            return JsonResponse({'error': 'Only support can send messages'}, status=403)
        
        if request.FILES:
            file = request.FILES.get('file')
            message_text = request.POST.get('message', '').strip()
            
            if not file:
                return JsonResponse({'error': 'File is required'}, status=400)
            
            file_type = get_file_type_from_extension(file.name)
            
            unique_id = uuid.uuid4().hex[:8]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = os.path.splitext(file.name)[1]
            final_file_name = f"{timestamp}_{unique_id}{ext}"
            
            upload_path = f'chat/attachments/{file_type}/{final_file_name}'
            saved_path = default_storage.save(upload_path, file)
            
            message = Message.objects.create(
                conversation=conversation,
                sender=support_user,
                message=message_text,
                is_from_support=True,
                is_read_by_support=True,
                is_read_by_user=False,
                attachment=saved_path,
                file_type=file_type,
                file_name=file.name
            )
        else:
            data = json.loads(request.body)
            message_text = data.get('message', '').strip()
            
            if not message_text:
                return JsonResponse({'error': 'Message is required'}, status=400)
            
            message = Message.objects.create(
                conversation=conversation,
                sender=support_user,
                message=message_text,
                is_from_support=True,
                is_read_by_support=True,
                is_read_by_user=False
            )
        
        conversation.last_message_at = timezone.now()
        conversation.unread_count_user += 1
        conversation.save()
        
        from apps.notification.models import Notification
        notification = Notification.objects.create(
            user=conversation.user,
            notification_type='chat_message',
            title='New message from support',
            message=f'You have a new message: {message_text[:50] if message_text else "File attachment"}...',
            related_object_type='conversation',
            related_object_id=conversation.id,
            data={'conversation_id': conversation.id, 'message_id': message.id}
        )
        
        print(f"🔔 ADMIN_VIEWS: Created notification ID={notification.id} for user ID={conversation.user.id} (admin user ID={request.user.id})")
        
        room_group_name = f'chat_{conversation_id}'
        channel_layer = get_channel_layer()
        
        if channel_layer:
            try:
                if message.attachment:
                    attachment_url = request.build_absolute_uri(message.attachment.url)
                else:
                    attachment_url = None
                
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message.message,
                        'sender': support_user.id,
                        'sender_id': support_user.id,
                        'sender_name': support_user.get_full_name() or support_user.username,
                        'is_from_support': True,
                        'created_at': message.created_at.isoformat(),
                        'message_id': message.id,
                        'attachment': attachment_url,
                        'attachment_url': attachment_url,
                        'file_type': message.file_type,
                        'file_name': message.file_name
                    }
                )
                
                notification_group_name = f'notifications_{conversation.user.id}'
                print(f"🔔 ADMIN_VIEWS: Sending notification to group '{notification_group_name}' (conversation.user.id={conversation.user.id}, admin user.id={request.user.id})")
                async_to_sync(channel_layer.group_send)(
                    notification_group_name,
                    {
                        'type': 'notification',
                        'notification': {
                            'id': notification.id,
                            'notification_type': notification.notification_type,  # Fixed: changed 'type' to 'notification_type'
                            'title': notification.title,
                            'message': notification.message,
                            'related_object_type': notification.related_object_type,
                            'related_object_id': notification.related_object_id,
                            'data': notification.data,
                            'created_at': notification.created_at.isoformat(),
                            'status': notification.status  # Fixed: changed 'is_read' to 'status' to match NotificationConsumer
                        }
                    }
                )
                print(f"🔔 ADMIN_VIEWS: Notification sent successfully to group '{notification_group_name}'")
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                import traceback
                traceback.print_exc()
        
        attachment_url_for_response = None
        if message.attachment:
            attachment_url_for_response = request.build_absolute_uri(message.attachment.url)
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'message': message.message,
                'sender': support_user.get_full_name() or support_user.username,
                'is_from_support': True,
                'created_at': message.created_at.isoformat(),
                'attachment': attachment_url_for_response,
                'file_type': message.file_type,
                'file_name': message.file_name
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def get_messages_api(request, conversation_id):
    """
    API endpoint for getting messages
    """
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        messages = Message.objects.filter(conversation=conversation).select_related('sender').order_by('created_at')
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'message': msg.message,
                'sender': msg.sender.get_full_name() if msg.sender else 'Unknown',
                'sender_name': msg.sender.get_full_name() if msg.sender else 'Unknown',
                'sender_id': msg.sender.id if msg.sender else None,
                'is_from_support': msg.is_from_support,
                'created_at': msg.created_at.isoformat(),
                'attachment': msg.attachment.url if msg.attachment else None,
                'file_type': msg.file_type,
                'file_name': msg.file_name
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'conversation': {
                'id': conversation.id,
                'user_name': conversation.user.get_full_name() if conversation.user else conversation.user.email,
                'user_type': conversation.user_type,
                'status': conversation.status,
                'subject': conversation.subject or 'No subject'
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

