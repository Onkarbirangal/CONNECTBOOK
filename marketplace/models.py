from django.db import models
from django.conf import settings


class MarketplaceListing(models.Model):
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics & Gadgets'),
        ('vehicles', 'Vehicles & Automotive'),
        ('home', 'Home & Garden'),
        ('apparel', 'Apparel & Accessories'),
        ('entertainment', 'Books, Movies & Music'),
        ('sports', 'Sports & Outdoors'),
        ('other', 'Other Items'),
    ]

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('pending', 'Sale Pending'),
        ('sold', 'Sold'),
    ]

    CONDITION_CHOICES = [
        ('new', 'Brand New'),
        ('like_new', 'Used - Like New'),
        ('good', 'Used - Good'),
        ('fair', 'Used - Fair'),
    ]

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='marketplace_listings')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    location = models.CharField(max_length=150, default='Local Area')
    image = models.ImageField(upload_to='marketplace/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_featured = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - ${self.price}"

    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/images/default-cover.svg'

    def can_manage(self, user):
        if not user or user.is_anonymous:
            return False
        return user == self.seller or user.is_superuser


class SavedListing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_listings')
    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'listing')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.listing.title}"


class MarketplaceImage(models.Model):
    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='marketplace/images/%Y/%m/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.listing.title}"


class MarketplaceInquiry(models.Model):
    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('replied', 'Replied'),
    ]

    listing = models.ForeignKey(MarketplaceListing, on_delete=models.CASCADE, related_name='inquiries')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='marketplace_inquiries')
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Inquiry from {self.buyer.username} on {self.listing.title}"
