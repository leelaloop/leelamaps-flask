# LeelaMaps

Hi! This is a basic build of LeelaMaps, a map notes platform for sharing basically anything with anyone.

You can try the demo at [leelamaps.com](https://leelamaps.com).

## Current Build
- **Backend:** Python + Flask
- **Frontend:** HTML, CSS, JavaScript
- **Origin:** Originally conceptualized with DeepSeek, with some edits by Grok.

## Current Features
- **User System:** User Registration + Login
- **Core Map:** Interactive map interface.
- **Posting Notes:** Press and hold anywhere on the map to create a new note, or use the button to post at your current location.
- **Note Management:** Edit notes and change their location after posting.
- **Dynamic Display:**
    - Displays a general description of the author's distance from the note's location.
    - Text size adjusts with the quantity of text: short notes have large text; long notes have small text.
- **Performance:** Viewport updating: primarily loads notes within the user's current screen view (preparing for scalability).
- **Search:** Simple search bar to find notes.

## Upcoming Features
Here is the roadmap for future development. We welcome contributions!

**Real-time & Community**
- [ ] **WebSockets:** Live loading of new notes on the map.
- [ ] Comments + reactions on notes.
- [ ] Friend/group request system.
- [ ] Direct messaging between users.
- [ ] Stream-style updates.

**User Experience & Profiles**
- [ ] Admin panel.
- [ ] User Profiles.
- [ ] "Friends only" privacy setting for notes.
- [ ] Custom privacy: select specific users, friends, or groups.
- [ ] Notifications: Save search configurations or specific notes to receive email/push notifications on changes.
- [ ] Option for multiple authors on a single note.

**Map & Notes Enhancements**
- [ ] Marker base color to reflect privacy, user-selected emoji, or custom art.
- [ ] Tips to remind user of privacy setting if set to "Public" near user's location.
- [ ] Advanced search: Include/Exclude layers; filter by author, post time, event time.
- [ ] Default & custom/shareable templates for notes (e.g., profile, survey, emergency).

**Media & Commerce**
- [ ] Note media gallery (image, audio, video).
- [ ] Options to set Title, Description, Price, and Quantity for each media item.
- [ ] Option to set event date(s) & time(s).
- [ ] Option to set location to user's GPS.
- [ ] Shopping basket for notes that have priced items.
- [ ] Vendor's guarantee: default/customizable legal framework for vendors to be responsible for fulfilling their own transactions.

**Infrastructure & Future Tech**
- [ ] Legal disclaimer: LeelaMaps does not guarantee any goods or services.
- [ ] Cross-platform native apps.
- [ ] Mesh network + decentralized hosting.
- [ ] IoT support.

## 🤝 Help Needed!

I am a busy mom of a toddler and caretaker for local agroecology projects, so my progress on this project is sporadic.

Please take a peek at the code and build what you can! Let me know any questions or feedback that you have.

**How to Contribute:**
1.  Fork the repository.
2.  Create a new branch for your feature (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.
