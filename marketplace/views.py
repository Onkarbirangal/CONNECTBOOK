from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import MarketplaceListing, SavedListing
from .forms import MarketplaceListingForm
from social.models import AuditLog


@login_required
def listing_list_view(request):
    category = request.GET.get('category', '').strip()
    condition = request.GET.get('condition', '').strip()
    query = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    tab = request.GET.get('tab', 'all')

    listings = MarketplaceListing.objects.all()

    if tab == 'my_listings':
        listings = listings.filter(seller=request.user)
    elif tab == 'saved':
        listings = listings.filter(saved_by__user=request.user)
    else:
        listings = listings.filter(status='available')

    if category:
        listings = listings.filter(category=category)

    if condition:
        listings = listings.filter(condition=condition)

    if query:
        listings = listings.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query))

    if min_price:
        try:
            listings = listings.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            listings = listings.filter(price__lte=float(max_price))
        except ValueError:
            pass

    featured_listings = MarketplaceListing.objects.filter(is_featured=True, status='available')[:4]
    my_listings_count = MarketplaceListing.objects.filter(seller=request.user).count()
    saved_count = SavedListing.objects.filter(user=request.user).count()
    saved_ids = set(SavedListing.objects.filter(user=request.user).values_list('listing_id', flat=True))

    return render(request, 'marketplace/listing_list.html', {
        'listings': listings,
        'featured_listings': featured_listings,
        'categories': MarketplaceListing.CATEGORY_CHOICES,
        'conditions': MarketplaceListing.CONDITION_CHOICES,
        'selected_category': category,
        'selected_condition': condition,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
        'tab': tab,
        'my_listings_count': my_listings_count,
        'saved_count': saved_count,
        'saved_ids': saved_ids,
    })


@login_required
def create_listing_view(request):
    from .models import MarketplaceImage
    if request.method == 'POST':
        form = MarketplaceListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.save()

            # Handle additional gallery images
            for img in request.FILES.getlist('additional_images'):
                MarketplaceImage.objects.create(listing=listing, image=img)

            AuditLog.objects.create(
                actor=request.user,
                action='MARKETPLACE_LISTING_CREATE',
                target_repr=f"Listing {listing.title} (${listing.price})",
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'listing_id': listing.id, 'price': str(listing.price)}
            )
            messages.success(request, f"Your listing '{listing.title}' is now live on Marketplace!")
            return redirect('marketplace:listing_detail', pk=listing.pk)
    else:
        form = MarketplaceListingForm()

    return render(request, 'marketplace/listing_form.html', {'form': form, 'title': 'Create Marketplace Listing'})


def listing_detail_view(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk)
    
    # Track view count
    listing.views_count += 1
    listing.save(update_fields=['views_count'])

    can_manage = listing.can_manage(request.user) if request.user.is_authenticated else False
    more_from_seller = MarketplaceListing.objects.filter(seller=listing.seller).exclude(pk=listing.pk)[:4]
    gallery_images = listing.images.all()

    return render(request, 'marketplace/listing_detail.html', {
        'listing': listing,
        'can_manage': can_manage,
        'more_from_seller': more_from_seller,
        'gallery_images': gallery_images,
    })


@login_required
def edit_listing_view(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk)
    if not listing.can_manage(request.user):
        messages.error(request, "You are not authorized to edit this listing.")
        return redirect('marketplace:listing_detail', pk=listing.pk)

    if request.method == 'POST':
        form = MarketplaceListingForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, "Listing updated successfully.")
            return redirect('marketplace:listing_detail', pk=listing.pk)
    else:
        form = MarketplaceListingForm(instance=listing)

    return render(request, 'marketplace/listing_form.html', {'form': form, 'listing': listing, 'title': f"Edit {listing.title}"})


@login_required
def delete_listing_view(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk)
    if not listing.can_manage(request.user):
        messages.error(request, "You are not authorized to delete this listing.")
        return redirect('marketplace:listing_detail', pk=listing.pk)

    if request.method == 'POST':
        title = listing.title
        listing.delete()
        AuditLog.objects.create(
            actor=request.user,
            action='MARKETPLACE_LISTING_DELETE',
            target_repr=f"Listing {title}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Listing '{title}' has been removed.")
        return redirect('marketplace:listing_list')

    return render(request, 'marketplace/listing_confirm_delete.html', {'listing': listing})


@login_required
def toggle_status_view(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk)
    if not listing.can_manage(request.user):
        messages.error(request, "Unauthorized.")
        return redirect('marketplace:listing_detail', pk=listing.pk)

    new_status = 'sold' if listing.status == 'available' else 'available'
    listing.status = new_status
    listing.save()
    messages.success(request, f"Listing marked as {new_status.capitalize()}.")
    return redirect('marketplace:listing_detail', pk=listing.pk)


@login_required
def toggle_save_listing_view(request, pk):
    listing = get_object_or_404(MarketplaceListing, pk=pk)
    saved = SavedListing.objects.filter(user=request.user, listing=listing).first()
    if saved:
        saved.delete()
        messages.success(request, f"Removed '{listing.title}' from your saved items.")
    else:
        SavedListing.objects.create(user=request.user, listing=listing)
        messages.success(request, f"Saved '{listing.title}' to your saved items.")
    return redirect(request.META.get('HTTP_REFERER', 'marketplace:listing_detail'))


@login_required
def send_inquiry_view(request, pk):
    from .models import MarketplaceInquiry
    from chat.models import Conversation, Message
    listing = get_object_or_404(MarketplaceListing, pk=pk)

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if not message_text:
            messages.error(request, "Please enter a message for the seller.")
            return redirect('marketplace:listing_detail', pk=listing.pk)

        # 1. Create MarketplaceInquiry
        MarketplaceInquiry.objects.create(
            listing=listing,
            buyer=request.user,
            message=message_text
        )

        # 2. Dispatch direct chat message if buyer != seller
        if listing.seller != request.user:
            conv = Conversation.get_or_create_direct(request.user, listing.seller)
            chat_content = f"Marketplace Inquiry on '{listing.title}' (${listing.price}):\n{message_text}"
            Message.objects.create(conversation=conv, sender=request.user, content=chat_content)

        messages.success(request, f"Inquiry sent to {listing.seller.get_display_name()}! Check your Messenger for replies.")
    return redirect('marketplace:listing_detail', pk=listing.pk)


@login_required
def seller_dashboard_view(request):
    from .models import MarketplaceInquiry
    user_listings = MarketplaceListing.objects.filter(seller=request.user).order_by('-created_at')
    active_count = user_listings.filter(status='available').count()
    sold_count = user_listings.filter(status='sold').count()
    total_views = sum(l.views_count for l in user_listings)
    inquiries = MarketplaceInquiry.objects.filter(listing__seller=request.user).select_related('listing', 'buyer', 'buyer__profile').order_by('-created_at')

    return render(request, 'marketplace/seller_dashboard.html', {
        'listings': user_listings,
        'active_count': active_count,
        'sold_count': sold_count,
        'total_views': total_views,
        'inquiries': inquiries,
    })
