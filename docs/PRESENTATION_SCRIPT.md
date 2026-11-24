# CONNECTBOOK – PROJECT PRESENTATION SCRIPT

**Project Title:** ConnectBook – Real Facebook-Style Social Networking Website  
**Duration:** 5–7 Minutes  
**Audience:** Faculty Evaluators, External Examiners, & Peers  

---

### Slide 1: Introduction (1 Minute)
> "Good morning respected professors and evaluators. Today, I am proud to present **ConnectBook** – a complete, modern social networking application inspired by Facebook.
> Our project tagline is: *Connect with Friends. Share Your World.*
> Unlike basic demo projects, ConnectBook is a fully database-driven, responsive application powered by Python 3.12, Django 5.2, Django Channels for real-time WebSockets, SQLite, and Bootstrap 5."

---

### Slide 2: Architectural Stack (1 Minute)
> "On the screen, you can see our architectural stack.
> - **Backend:** Django 5.2 with Daphne ASGI server handling both traditional HTTP requests and real-time WebSockets.
> - **Database:** SQLite with normalized relational models, foreign keys, indexes, and custom constraints.
> - **Frontend:** Django Template Inheritance, Bootstrap 5, Bootstrap Icons, and vanilla ES6 JavaScript with Fetch API.
> - **Design System:** Custom Facebook aesthetic with full light and dark mode toggling."

---

### Slide 3: Core Features Demonstration (2.5 Minutes)
> "Let's walk through the core features:
> 1. **News Feed & Composer:** A classic 3-column desktop layout. Users can post text, images, and videos with audience selectors (Public, Friends, Only Me).
> 2. **Facebook Reactions & Comments:** We built all 6 familiar reactions—Like, Love, Haha, Wow, Sad, and Angry—with dynamic hover pickers and nested comment replies.
> 3. **24-Hour Stories:** Users can share photo, video, or colorful gradient text stories that automatically expire after 24 hours. The full-screen viewer includes animated progress bars and slide navigation.
> 4. **Real-Time Messenger:** Built using Django Channels and WebSockets. Users can chat 1-on-1 with live typing indicators and instant delivery.
> 5. **Communities & Groups:** Public and private groups with dedicated timelines and join approval workflows.
> 6. **Search & Memories:** Autocomplete search for people, groups, and hashtags, alongside an 'On This Day' memories engine."

---

### Slide 4: Security & Administration (1 Minute)
> "Security is implemented at every layer:
> - CSRF and XSS protection.
> - Granular object-level permissions preventing unauthorized data access.
> - Staff administrative dashboard with 7-day registration and activity charts.
> - An active Moderation Queue where administrators can review reported content, remove violations, and track changes in immutable audit logs."

---

### Slide 5: Testing & Conclusion (30 Seconds)
> "The platform has been validated with automated test cases covering authentication, privacy rules, and REST APIs.
> In conclusion, ConnectBook demonstrates how modern web standards and Python/Django can power a real-world, scalable social networking product.
> Thank you, and I am now ready to take your questions."
