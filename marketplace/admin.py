from django.contrib import admin
from .models import MarketplaceListing


@admin.register(MarketplaceListing)
class MarketplaceListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'category', 'price', 'location', 'status', 'created_at')
    search_fields = ('title', 'description', 'seller__username', 'location')
    list_filter = ('category', 'status')
