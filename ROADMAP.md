# Roadmap: Element Announce Bot

This roadmap outlines the plan for polishing the Admin UI, expanding automation, and implementing features to maximize organic social media sharing and engagement.

---

## Phase 1: UI/UX Polish

Enhance the visual appeal, responsiveness, and user feedback loops of the CustomTkinter desktop interface.

### Key Features
- [ ] **Modern Dashboard View**: Replace the plain list of announcements with a grid of visual "cards" displaying announcement status, recipient count, and engagement rate metrics.
- [ ] **Dynamic Toast Notifications**: Implement sleek, fade-in/out toast notifications for success/error alerts instead of appending logs to a static text panel.
- [ ] **Interactive Charts**: Integrate matplotlib/tkinter charts to show historical engagement curves (e.g., how quickly team members react with ✅ after a message is sent).
- [ ] **Custom Styling & Dark Mode**: Provide a theme switcher in settings (System / Light / Sleek Dark mode with cyberpunk/neon accents).
- [ ] **Progress Bars**: Add animated progress bars showing real-time delivery status when broadcasting to many users.

---

## Phase 2: Advanced Automation

Introduce scheduling, smart templates, and recovery systems to streamline operations.

### Key Features
- [ ] **Scheduled Announcements**: Add a scheduler using a background thread (`cron` / `apscheduler`) to allow queuing announcements for a specific time and date.
- [ ] **Auto-Retry & Recovery**: Implement automatic queuing and retry logic for users who are temporarily offline or have encryption sync errors.
- [ ] **Smart Templates**: A template creator allowing admins to save and reuse common message layouts with placeholders (e.g., `{member_name}`, `{date}`).
- [ ] **Inactive Member Ping**: Automatically send a gentle private reminder DM to team members who haven't reacted to an announcement within 24 hours.

---

## Phase 3: Organic Sharing & Social Media Loops

Maximize engagement and facilitate organic sharing of company updates to public social networks.

### Key Features
- [ ] **Auto-Generated Announcement Cards**:
  - Integrate a PIL-based image generator that automatically turns text announcements into highly styled, branded visual cards/graphics.
  - Save these cards directly to the admin system so they can be downloaded or shared.
- [ ] **One-Click Share Buttons (X / LinkedIn)**:
  - Add native sharing buttons next to each announcement in the GUI.
  - Implement composer URL integrations (e.g., `https://twitter.com/intent/tweet?text=...`) to allow the admin or members to share updates publicly with a single click.
- [ ] **Viral Loop "Click-to-Tweet" Links**:
  - Automatically append short click-to-tweet links at the bottom of DMs sent to members, encouraging them to share the achievement or update on their personal social media profiles.
- [ ] **Engagement Leaderboard**:
  - Create a gamified "Engagement Leaderboard" tab in the GUI, displaying the most active members who react the fastest, promoting internal culture and friendly competition.
