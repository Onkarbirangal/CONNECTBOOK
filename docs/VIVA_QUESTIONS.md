# CONNECTBOOK – COLLEGE VIVA QUESTIONS & ANSWERS

### Q1: Why did you choose Django and SQLite for ConnectBook?
**Answer:** Django provides a robust, battery-included framework with built-in authentication, ORM security, and template inheritance, eliminating boilerplate. SQLite is serverless, lightweight, requires zero external configuration, and easily supports hundreds of concurrent reads for desktop and local demonstrations.

### Q2: How is real-time messaging implemented without Redis?
**Answer:** We used **Django Channels** and **Daphne** with `InMemoryChannelLayer`. Daphne acts as an ASGI server capable of handling persistent WebSocket connections (`ws://`). The in-memory channel layer routes messages across active consumer groups directly in memory. For maximum reliability, we also engineered an automated HTTP polling fallback.

### Q3: How do you prevent duplicate friendships in the database?
**Answer:** In the `Friendship` model, we enforce canonical ordering on `save()` such that `user1_id` is always strictly less than `user2_id`. Combined with a `unique_together = ('user1', 'user2')` constraint, this makes it mathematically impossible for duplicate friendship rows like `(A, B)` and `(B, A)` to coexist.

### Q4: How is post privacy enforced?
**Answer:** Privacy is enforced at the backend through model querysets and a custom `can_view(user)` method. When a user requests the feed or a profile, the query filters out:
1. Blocked users
2. "Friends Only" posts if the requester is not a confirmed friend
3. "Only Me" posts if the requester is not the author.

### Q5: How do 24-hour stories automatically expire?
**Answer:** When a story is created, its `expires_at` timestamp is set to `timezone.now() + timedelta(hours=24)`. Database queries filtering active stories strictly check `expires_at__gt=timezone.now()`. When the 24-hour window lapses, the story is automatically omitted from feed carousels and viewer endpoints without requiring periodic batch deletions.

### Q6: How does the Facebook reaction system work?
**Answer:** The `Reaction` model uses a `unique_together = ('user', 'post')` constraint. When a user clicks or hovers over the like button, an AJAX POST request is dispatched to `/posts/<id>/react/`. The view either updates the reaction type (e.g. from Like to Love) or removes it if toggled off, returning updated counts and user status as JSON without full page reload.

### Q7: How are user passwords secured?
**Answer:** Django hashes passwords using the industry-standard PBKDF2 algorithm with SHA-256 iterations and random salt strings. Passwords are never stored as plain text, defending against rainbow table attacks.
