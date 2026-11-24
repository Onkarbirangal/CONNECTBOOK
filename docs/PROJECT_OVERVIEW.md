# CONNECTBOOK – PROJECT OVERVIEW

## 1. Executive Summary
**ConnectBook** is a modern social networking platform engineered from the ground up to mirror the core user experience and architecture of Facebook. It provides users with a cohesive digital environment to connect with friends, share thoughts, upload photos and videos, react with expressive emojis, post ephemeral 24-hour stories, join interest-driven communities, and communicate privately in real-time.

## 2. Problem Statement & Motivation
Modern web applications demand high responsiveness, real-time interactivity, privacy guarantees, and intuitive user experiences. ConnectBook demonstrates how a production-style social networking website can be created using **Django 5.2, Django Channels, WebSockets, and Bootstrap 5** without relying on complex, heavyweight single-page application (SPA) frameworks like React or Node.js.

## 3. Core Objectives
- **Familiar UI/UX:** Provide a 3-column layout matching the Facebook standard (left navigation, center feed, right contacts & suggestions).
- **Relational Integrity:** Maintain clean database relationships using Django ORM and SQLite with canonical ordering for friendships.
- **Real-Time Communication:** Implement low-latency messaging and notification badges via WebSockets and Django Channels with automated HTTP fallback.
- **Privacy by Design:** Enforce granular permissions for public, friends-only, and private content both on the UI and database queries.
- **Community Safety:** Include content reporting, administrative moderation queues, and audit logs.
