from django.contrib import admin
from .models import Conversation, ConversationParticipant, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_group', 'updated_at')

@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'user', 'is_admin', 'joined_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'is_read', 'created_at')
