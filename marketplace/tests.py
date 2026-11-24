from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from marketplace.models import MarketplaceListing, MarketplaceInquiry
from chat.models import Message

User = get_user_model()


class MarketplaceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.seller = User.objects.create_user(username='seller1', email='seller@example.com', password='Password123!')
        self.buyer = User.objects.create_user(username='buyer1', email='buyer@example.com', password='Password123!')
        self.client.login(username='seller1', password='Password123!')

    def test_create_and_manage_listing(self):
        res = self.client.post(reverse('marketplace:create_listing'), {
            'title': '27-inch 4K Monitor',
            'price': '299.99',
            'category': 'electronics',
            'condition': 'like_new',
            'location': 'Downtown',
            'description': 'Ultra HD IPS display with USB-C.',
            'status': 'available',
        })
        self.assertEqual(res.status_code, 302)
        listing = MarketplaceListing.objects.filter(title='27-inch 4K Monitor').first()
        self.assertIsNotNone(listing)
        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.condition, 'like_new')

        # Toggle status to sold
        toggle_res = self.client.post(reverse('marketplace:toggle_status', kwargs={'pk': listing.pk}))
        self.assertEqual(toggle_res.status_code, 302)
        listing.refresh_from_db()
        self.assertEqual(listing.status, 'sold')

    def test_v6_marketplace_inquiry_and_dashboard(self):
        # 1. Create listing
        listing = MarketplaceListing.objects.create(
            seller=self.seller,
            title='Vintage Leather Jacket',
            price='120.00',
            category='clothing',
            condition='good',
            location='Brooklyn',
            status='available',
            views_count=15
        )

        # 2. Buyer views listing detail (increments views)
        self.client.login(username='buyer1', password='Password123!')
        detail_res = self.client.get(reverse('marketplace:listing_detail', kwargs={'pk': listing.pk}))
        self.assertEqual(detail_res.status_code, 200)
        listing.refresh_from_db()
        self.assertEqual(listing.views_count, 16)

        # 3. Buyer sends inquiry
        inq_res = self.client.post(reverse('marketplace:send_inquiry', kwargs={'pk': listing.pk}), {
            'message': 'Hi! Is this leather jacket still available? Would you accept $100?'
        })
        self.assertEqual(inq_res.status_code, 302)

        # Verify MarketplaceInquiry created
        inquiry = MarketplaceInquiry.objects.filter(listing=listing, buyer=self.buyer).first()
        self.assertIsNotNone(inquiry)
        self.assertIn('$100', inquiry.message)

        # Verify chat message dispatched
        chat_msg = Message.objects.filter(sender=self.buyer).first()
        self.assertIsNotNone(chat_msg)
        self.assertIn('Marketplace Inquiry', chat_msg.content)

        # 4. Seller checks dashboard
        self.client.login(username='seller1', password='Password123!')
        dash_res = self.client.get(reverse('marketplace:seller_dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertEqual(dash_res.context['active_count'], 1)
        self.assertEqual(dash_res.context['total_views'], 16)
        self.assertEqual(len(dash_res.context['inquiries']), 1)
