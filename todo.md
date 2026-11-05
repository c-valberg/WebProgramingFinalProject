================================
Before submitting today (checkpoint polish)
================================
 Get my chores.html working. It has stray JS and isn’t routed, so it’s dead weight.
 Seed 1-2 more demo users so the board looks like a household.
 Fill out the rubric and record the demo video.

================================
Core chore features
================================
 Mark a chore done: the done column exists but nothing uses it yet. Add a checkbox on each card and a PATCH /api/chores/<id> for it.
 Add the ability to delete or edit a chore with the same permission rule as moving (admin, or yours/unassigned).
 Due dates and/or recurring chores (weekly, daily).
 Replace the alert() on a failed move with a Bootstrap toast.
 Show completed chores differently, e.g. strikethrough or a separate section.

================================
Fairness features (from your feedback)
================================
 Add a Preference model (user_id, chore_id, rating, e.g. -2 to +2).
 Add a right-click or long-press popup on each chore card for like/dislike, which is the idea you noted in mychores.html.
 Add an “Auto-assign unassigned chores” admin button that uses preferences to spread the work fairly. A simple version is to give each chore to the lowest-workload member who doesn’t strongly dislike it.
 Show a per-person workload summary, like a count or “points” per member, so fairness is visible.
 Color-code each chore card by assignee, the “sticky note” idea from the feedback.
 Decide on the drag rule. Your feedback suggested limiting drags to your own column or the chore’s auto-assigned owner. Right now it’s mine or unassigned. Pick one and justify it in your write-up.
================================
Users and admin
================================
 Add admin tools to create and remove members and change roles.
 Add a registration or invite flow, or at least a “create user” form for admins.
 Add a role-protected admin route that returns 403 for members, which is good rubric evidence for authorization.
 Add a password change page.

================================
Security and cleanup
================================
 Move SECRET_KEY to an environment variable.
 Hash-check and rate-limit login attempts, if you want extra credit territory.
 Add custom 403/404 error pages.
 Remove package.json / react-sortablejs if you’re staying with plain SortableJS from the CDN, or switch to bundling it.
 Write a short README with setup steps (pip install -r requirements.txt, run command, demo logins).
 Write a few tests for the permission rules in move_chore.