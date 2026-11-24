from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from accounts.models import UserProfile, UserPreference
from friends.models import Friendship, FriendRequest
from social.models import Post, Reaction, Comment, SavedPost, Hashtag
from stories.models import Story
from groups_app.models import Group, GroupMembership
from chat.models import Conversation, ConversationParticipant, Message
from notifications.models import Notification
from pages_app.models import Page, PageFollow
from events_app.models import Event, EventRSVP
from marketplace.models import MarketplaceListing
from streaming.models import LiveStream
from accounts.models import Follow, UserPrivacySetting

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds database with realistic ConnectBook social media data.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding ConnectBook database...")

        # 1. Create Superuser / Admin
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@connectbook.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('Admin@12345')
        admin_user.save()
        admin_profile = admin_user.profile
        admin_profile.bio = "System Administrator & Lead Architect of ConnectBook."
        admin_profile.work = "ConnectBook Inc."
        admin_profile.city = "San Francisco, CA"
        admin_profile.education = "Stanford University"
        admin_profile.save()

        # 2. Create Realistic Demo Users
        demo_users_data = [
            {
                'username': 'sarah_c',
                'email': 'sarah@example.com',
                'first_name': 'Sarah',
                'last_name': 'Connor',
                'gender': 'female',
                'dob': date(1998, 5, 14),
                'bio': "Software engineer, hiker, coffee lover ☕ | Building cool things on the web.",
                'city': 'Seattle, WA',
                'work': 'CloudScale Systems',
                'education': 'University of Washington',
            },
            {
                'username': 'alex_r',
                'email': 'alex@example.com',
                'first_name': 'Alex',
                'last_name': 'Rivera',
                'gender': 'male',
                'dob': date(1996, 9, 22),
                'bio': "Photographer & travel enthusiast 📷✈️ Chasing golden hour everywhere.",
                'city': 'Austin, TX',
                'work': 'Rivera Creative Studio',
                'education': 'UT Austin',
            },
            {
                'username': 'emily_w',
                'email': 'emily@example.com',
                'first_name': 'Emily',
                'last_name': 'Watson',
                'gender': 'female',
                'dob': date(2000, 3, 10),
                'bio': "Product designer & typography geek ✨ Creating simple human experiences.",
                'city': 'New York, NY',
                'work': 'Designcraft UI',
                'education': 'Parsons School of Design',
            },
            {
                'username': 'david_kim',
                'email': 'david@example.com',
                'first_name': 'David',
                'last_name': 'Kim',
                'gender': 'male',
                'dob': date(1997, 11, 30),
                'bio': "Full-stack developer | Open-source contributor 🚀 AI & Python fanatic.",
                'city': 'San Jose, CA',
                'work': 'NextWave Labs',
                'education': 'UC Berkeley',
            },
            {
                'username': 'sophia_m',
                'email': 'sophia@example.com',
                'first_name': 'Sophia',
                'last_name': 'Martinez',
                'gender': 'female',
                'dob': date(1999, 7, 18),
                'bio': "Digital marketer & foodie 🥑 Sharing marketing tips and good vibes.",
                'city': 'Chicago, IL',
                'work': 'Apex Growth Media',
                'education': 'Northwestern University',
            },
        ]

        created_users = [admin_user]
        for data in demo_users_data:
            u, _ = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'gender': data['gender'],
                    'date_of_birth': data['dob'],
                }
            )
            u.set_password('Password@123')
            u.save()

            prof = u.profile
            prof.bio = data['bio']
            prof.city = data['city']
            prof.work = data['work']
            prof.education = data['education']
            prof.save()
            created_users.append(u)

        # 3. Create Friendships & Requests
        u0, u1, u2, u3, u4, u5 = created_users[0], created_users[1], created_users[2], created_users[3], created_users[4], created_users[5]

        Friendship.objects.get_or_create(user1=u0, user2=u1)
        Friendship.objects.get_or_create(user1=u0, user2=u2)
        Friendship.objects.get_or_create(user1=u1, user2=u2)
        Friendship.objects.get_or_create(user1=u1, user2=u3)
        Friendship.objects.get_or_create(user1=u2, user2=u4)
        Friendship.objects.get_or_create(user1=u3, user2=u4)
        Friendship.objects.get_or_create(user1=u4, user2=u5)

        # Pending friend request to admin
        FriendRequest.objects.get_or_create(sender=u5, receiver=u0, defaults={'status': 'pending'})

        # 4. Create Groups
        g1, _ = Group.objects.get_or_create(
            name='Tech & Open Source Developers',
            defaults={
                'description': 'A vibrant community of developers, builders, and designers discussing Python, Django, WebSockets, and modern technology.',
                'privacy': 'public',
                'creator': u4,
            }
        )
        GroupMembership.objects.get_or_create(group=g1, user=u4, defaults={'role': 'admin'})
        GroupMembership.objects.get_or_create(group=g1, user=u0, defaults={'role': 'member'})
        GroupMembership.objects.get_or_create(group=g1, user=u1, defaults={'role': 'member'})

        g2, _ = Group.objects.get_or_create(
            name='Photography & Travel Hub',
            defaults={
                'description': 'Share your best travel shots, camera settings, landscape tips, and gear reviews.',
                'privacy': 'public',
                'creator': u2,
            }
        )
        GroupMembership.objects.get_or_create(group=g2, user=u2, defaults={'role': 'admin'})
        GroupMembership.objects.get_or_create(group=g2, user=u0, defaults={'role': 'member'})
        GroupMembership.objects.get_or_create(group=g2, user=u3, defaults={'role': 'member'})

        # 5. Create Posts
        p1, _ = Post.objects.get_or_create(
            author=u1,
            content="Excited to be on ConnectBook! Just launched a new feature using Django Channels and WebSockets. Real-time updates feel magical when everything clicks! 🚀💻 #django #python #connectbook",
            defaults={'privacy': 'public'}
        )

        p2, _ = Post.objects.get_or_create(
            author=u2,
            content="Golden hour over the mountains this evening. Nature never fails to amaze. Remember to take a break from your screens this weekend everyone! 🌄🌲✨ #outdoors #photography #weekendvibes",
            defaults={'privacy': 'public'}
        )

        p3, _ = Post.objects.get_or_create(
            author=u3,
            content="Working on a clean new design system today. Minimalist cards, subtle shadows, and crisp typography always win. What do you prioritize in modern UI design? #design #uiux",
            defaults={'privacy': 'public'}
        )

        p4, _ = Post.objects.get_or_create(
            author=u4,
            content="Friendly reminder: Never stop learning. Technology moves fast, but strong fundamentals in data structures, architecture, and database design will always stay relevant. 💡",
            defaults={'privacy': 'friends'}
        )

        p5, _ = Post.objects.get_or_create(
            author=u0,
            content="Welcome everyone to ConnectBook! Connect with Friends. Share Your World. Feel free to explore groups, stories, and real-time messaging. 🎉",
            defaults={'privacy': 'public'}
        )

        # 6. Reactions
        Reaction.objects.get_or_create(user=u0, post=p1, defaults={'reaction_type': 'like'})
        Reaction.objects.get_or_create(user=u2, post=p1, defaults={'reaction_type': 'love'})
        Reaction.objects.get_or_create(user=u3, post=p1, defaults={'reaction_type': 'wow'})
        Reaction.objects.get_or_create(user=u1, post=p2, defaults={'reaction_type': 'love'})
        Reaction.objects.get_or_create(user=u0, post=p2, defaults={'reaction_type': 'like'})
        Reaction.objects.get_or_create(user=u4, post=p3, defaults={'reaction_type': 'haha'})

        # 7. Comments & Replies
        c1, _ = Comment.objects.get_or_create(
            post=p1,
            author=u0,
            content="Awesome milestone, Sarah! WebSockets make real-time feeds so smooth."
        )
        Comment.objects.get_or_create(
            post=p1,
            author=u1,
            parent=c1,
            content="Thanks! Couldn't agree more."
        )
        Comment.objects.get_or_create(
            post=p2,
            author=u3,
            content="Incredible shot, Alex! What camera lens did you use?"
        )

        # 8. Active Stories
        Story.objects.get_or_create(
            author=u1,
            text_content="Starting the day with good coffee and fresh code! ☕💻",
            media_type='text',
            background_color='linear-gradient(135deg, #1877F2 0%, #00C6FF 100%)',
            defaults={'expires_at': timezone.now() + timedelta(hours=22)}
        )
        Story.objects.get_or_create(
            author=u2,
            text_content="Catching the morning sun in Austin ☀️",
            media_type='text',
            background_color='linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            defaults={'expires_at': timezone.now() + timedelta(hours=20)}
        )

        # 9. Direct Conversation & Messages
        conv, _ = Conversation.objects.get_or_create(is_group=False)
        ConversationParticipant.objects.get_or_create(conversation=conv, user=u0)
        ConversationParticipant.objects.get_or_create(conversation=conv, user=u1)

        Message.objects.get_or_create(
            conversation=conv,
            sender=u1,
            content="Hey! Welcome to ConnectBook. Let me know what you think of the new features."
        )
        Message.objects.get_or_create(
            conversation=conv,
            sender=u0,
            content="Hey Sarah! The feed and real-time messenger look fantastic!"
        )

        # 10. Notifications
        Notification.objects.get_or_create(
            recipient=u0,
            actor=u1,
            notification_type='post_comment',
            title='New Comment',
            message="Sarah Connor commented on your post.",
            target_url=f"/#post-{p5.id}"
        )
        Notification.objects.get_or_create(
            recipient=u0,
            actor=u5,
            notification_type='friend_request',
            title='Friend Request',
            message="Sophia Martinez sent you a friend request.",
            target_url="/friends/"
        )

        # 11. Follow Relationships
        Follow.objects.get_or_create(follower=u1, followed=u0)
        Follow.objects.get_or_create(follower=u2, followed=u0)
        Follow.objects.get_or_create(follower=u3, followed=u1)
        Follow.objects.get_or_create(follower=u0, followed=u1)

        # 12. Pages & Page Followers
        page1, _ = Page.objects.get_or_create(
            name="ConnectBook Tech & Engineering",
            defaults={
                'slug': 'connectbook-tech',
                'category': 'business',
                'bio': 'Official Engineering & Open Source Updates from ConnectBook.',
                'description': 'Behind-the-scenes architectural insights, performance enhancements, and web engineering updates.',
                'website': 'https://github.com/connectbook',
                'email': 'engineering@connectbook.com',
                'owner': u0,
                'is_verified': True,
            }
        )
        PageFollow.objects.get_or_create(page=page1, user=u0)
        PageFollow.objects.get_or_create(page=page1, user=u1)
        PageFollow.objects.get_or_create(page=page1, user=u2)

        page2, _ = Page.objects.get_or_create(
            name="Pacific Northwest Photography Club",
            defaults={
                'slug': 'pnw-photography-club',
                'category': 'creator',
                'bio': 'Capturing the majesty of Puget Sound, Rainier, and Olympic peaks.',
                'description': 'A vibrant community of professional and amateur photographers across the PNW.',
                'owner': u1,
                'is_verified': True,
            }
        )
        PageFollow.objects.get_or_create(page=page2, user=u1)
        PageFollow.objects.get_or_create(page=page2, user=u3)

        # 13. Events & RSVPs
        event1, _ = Event.objects.get_or_create(
            title="Global Developer Summit 2026",
            defaults={
                'description': 'Join software architects and developers worldwide for keynote talks, workshops, and lightning discussions.',
                'organizer': u0,
                'venue': 'Moscone West & Virtual Stream',
                'start_time': timezone.now() + timedelta(days=5),
                'end_time': timezone.now() + timedelta(days=5, hours=6),
                'privacy': 'public',
            }
        )
        EventRSVP.objects.get_or_create(event=event1, user=u0, defaults={'status': 'going'})
        EventRSVP.objects.get_or_create(event=event1, user=u1, defaults={'status': 'going'})
        EventRSVP.objects.get_or_create(event=event1, user=u2, defaults={'status': 'interested'})

        event2, _ = Event.objects.get_or_create(
            title="Seattle Weekend Coffee & Code",
            defaults={
                'description': 'Casual weekend meetup for coffee, laptops, open-source hacking, and friendly chats.',
                'organizer': u1,
                'venue': 'Victrola Coffee Roasters, Pike St, Seattle',
                'start_time': timezone.now() + timedelta(days=2),
                'end_time': timezone.now() + timedelta(days=2, hours=3),
                'privacy': 'public',
            }
        )
        EventRSVP.objects.get_or_create(event=event2, user=u1, defaults={'status': 'going'})
        EventRSVP.objects.get_or_create(event=event2, user=u3, defaults={'status': 'going'})

        # 14. Marketplace Listings
        MarketplaceListing.objects.get_or_create(
            title="Sony Alpha A7 IV Mirrorless Camera (Like New)",
            seller=u1,
            defaults={
                'description': 'Immaculate condition with box, charger, two batteries, and 28-70mm lens. Low shutter count.',
                'price': 1850.00,
                'category': 'electronics',
                'location': 'Seattle, WA',
                'status': 'available',
            }
        )
        MarketplaceListing.objects.get_or_create(
            title="Custom Mechanical Keyboard (Lubed Gateron Oil Kings)",
            seller=u2,
            defaults={
                'description': 'Keychron Q1 Pro aluminum build, custom PBT keycaps, gasket mounted, hot-swappable.',
                'price': 175.00,
                'category': 'electronics',
                'location': 'Austin, TX',
                'status': 'available',
            }
        )
        MarketplaceListing.objects.get_or_create(
            title="Vintage Mid-Century Walnut Coffee Table",
            seller=u3,
            defaults={
                'description': 'Solid walnut with brass tipped tapered legs. Minor surface patina, very sturdy.',
                'price': 220.00,
                'category': 'home',
                'location': 'New York, NY',
                'status': 'available',
            }
        )

        # 15. Live Stream Studio Sessions
        LiveStream.objects.get_or_create(
            title="ConnectBook Live Engineering: Architecture Q&A",
            host=u0,
            defaults={
                'description': 'Deep dive into Django 5.2, Channels WebSockets, SQLite optimizations, and responsive UI layout.',
                'status': 'live',
                'viewer_count': 32,
                'scheduled_start': timezone.now() - timedelta(minutes=15),
                'actual_start': timezone.now() - timedelta(minutes=15),
            }
        )
        LiveStream.objects.get_or_create(
            title="PNW Nature Photo Walk: Live Editing in Lightroom",
            host=u1,
            defaults={
                'description': 'Editing RAW files from Mount Rainier sunrise walk. Color grading and composition tips.',
                'status': 'scheduled',
                'scheduled_start': timezone.now() + timedelta(days=1),
            }
        )

        self.stdout.write(self.style.SUCCESS("ConnectBook database seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("Admin account: username=admin, password=Admin@12345"))
        self.stdout.write(self.style.SUCCESS("Demo account: username=sarah_c, password=Password@123"))
