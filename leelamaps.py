# leelamaps.py - LeelaMaps with public/private notes + username display

from flask import Flask, render_template_string, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func
import os

app = Flask(__name__)

# Config
app.secret_key = 'super-secret-key-please-change-in-prod-2026'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'leelamaps.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)                      # ← correct placement

login_manager = LoginManager()
login_manager.init_app(app)  # Initialize with app
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# if __name__ == '__main__':
#     # You can keep init_db() if you want, but after migrations it's optional
#     # with app.app_context():
#     #     db.create_all()
#     app.run(debug=True)

# ----------------------
# Models
# ----------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Add these fields to your Note class in the Models section
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    text = db.Column(db.Text, nullable=False)
    privacy = db.Column(db.String(20), nullable=False, default='private')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='notes')
    
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    user_lat = db.Column(db.Float, nullable=True)
    user_lng = db.Column(db.Float, nullable=True)
    
    # NEW FIELDS FOR SEARCH
    address = db.Column(db.String(500), nullable=True)  # Full formatted address
    place_name = db.Column(db.String(200), nullable=True)  # City/Place name
    country = db.Column(db.String(100), nullable=True)
    search_vector = db.Column(db.String(1000), nullable=True)  # Combined searchable text
# ----------------------
# Init DB
# ----------------------
def init_db():
    with app.app_context():
        db.create_all()

# ----------------------
# Routes
# ----------------------
@app.route('/')
@login_required
def index():
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#f0f4f8">
        <title>LeelaMaps</title>
        
        <!-- Mapbox GL JS CSS -->
        <link href="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.css" rel="stylesheet">
        
        <!-- Mapbox GL JS -->
        <script src="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.js"></script>
        
        <style>
            /* Fix body layout */
            html, body { 
                height: 100%; 
                margin: 0; 
                padding: 0; 
                font-family: Arial, sans-serif; 
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }

            /* Header styles */
            header {
                padding: 10px 15px;
                background: #f0f4f8;
                border-bottom: 1px solid #ccc;
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: relative;
                z-index: 1000;
                flex-wrap: wrap;
                gap: 10px;
            }

            /* Map container */
            #map-container {
                flex: 1;
                width: 100%;
                position: relative;
                overflow: hidden;
            }

            /* Map takes full container */
            #map { 
                height: 100%; 
                width: 100%; 
                position: absolute;
                top: 0;
                left: 0;
            }

            /* Flash messages */
            .flash { 
                padding: 10px; 
                margin: 10px 20px; 
                border-radius: 4px; 
                flex-shrink: 0;
            }
            .success { background: #e6ffed; color: #006400; }
            .error   { background: #ffe6e6; color: #8b0000; }

            /* Loading spinner for mobile */
            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #3498db;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            /* Better flash messages on mobile */
            .flash {
                margin: 5px 10px !important;
                padding: 12px !important;
                font-size: 14px;
                border-radius: 8px !important;
            }

            /* User menu */
            .user-menu-container { position: relative; }
            .user-trigger {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 50%;
                width: 44px;
                height: 44px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: white;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                transition: background-color 0.2s;
            }
            .user-trigger:hover {
                background: #f0f0f0;
            }

            .user-trigger:active {
                background: #e0e0e0;
            }
            .user-dropdown {
                display: none;
                position: absolute;
                top: 100%;
                right: 0;
                background: white;
                border: 1px solid #ccc;
                border-radius: 6px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                min-width: 160px;
                z-index: 1000;
                margin-top: 4px;
            }
            .user-dropdown.show {
                display: block;
            }

            .user-dropdown .user-info {
                padding: 15px;
                border-bottom: 1px solid #eee;
            }

            .user-dropdown .username {
                font-weight: bold;
                color: #333;
            }
            .user-dropdown .email {
                font-size: 12px;
                color: #666;
                margin-top: 3px;
            }

            .user-dropdown a {
                display: block;
                padding: 12px 15px;
                color: #333;
                text-decoration: none;
                transition: background 0.2s;
            }
            .user-dropdown a:hover {
                background: #f5f5f5;
            }

            .user-dropdown a.logout {
                color: #d32f2f;
                border-top: 1px solid #eee;
            }


            /* Dynamic text sizing - MUST COME FIRST */
            .dynamic-text {
                transition: font-size 0.2s ease;
                line-height: 1.4;
            }

            /* Size classes - in order of size */
            .text-size-xxl { font-size: 24px; font-weight: 600; }
            .text-size-xl { font-size: 20px; font-weight: 500; }
            .text-size-lg { font-size: 18px; font-weight: 400; }
            .text-size-md { font-size: 16px; font-weight: 400; }
            .text-size-sm { font-size: 14px; font-weight: 400; color: #444; }
            .text-size-xs { font-size: 12px; font-weight: 400; color: #555; }

            /* For the note text in popups */
            .note-text {
                transition: font-size 0.2s ease;
                max-height: 300px;
                overflow-y: auto;
                padding: 5px 0;
            }

            /* For the textarea in forms */
            .dynamic-textarea {
                transition: font-size 0.2s ease, height 0.2s ease;
                resize: vertical;
                min-height: 100px;
            }

            /* Smooth transitions */
            .dynamic-text, .dynamic-textarea {
                transition: font-size 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                            height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }




            /* Dialog/modal styles */
            dialog {
                border: none; 
                border-radius: 8px; 
                padding: 20px; 
                width: 90%; 
                max-width: 500px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                margin: 0;
                z-index: 2000;
            }
            dialog::backdrop { 
                background: rgba(0,0,0,0.5); 
            }
            .modal-header { 
                margin-bottom: 15px; 
                font-size: 1.3em; 
                font-weight: bold; 
            }
            textarea { 
                width: 100%; 
                height: 120px; 
                padding: 10px; 
                border: 1px solid #ccc; 
                border-radius: 4px; 
                resize: vertical; 
                box-sizing: border-box;
            }
            .privacy-toggle { 
                display: flex; 
                gap: 20px; 
                margin: 15px 0; 
            }
            .privacy-toggle label { 
                display: flex; 
                align-items: center; 
                gap: 6px; 
                cursor: pointer; 
                font-size: 1.1em; 
            }
            .privacy-toggle input[type="radio"] { 
                width: 18px; 
                height: 18px; 
            }
            .modal-buttons { 
                display: flex; 
                justify-content: flex-end; 
                gap: 10px; 
                margin-top: 20px; 
            }
            button { 
                padding: 10px 18px; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer; 
            }
            #saveNote { 
                background: #4CAF50; 
                color: white; 
            }
            #cancelNote { 
                background: #aaa; 
                color: white; 
            }
            .note-user { 
                font-weight: bold; 
                color: #1a3c5e; 
            }
            .note-privacy { 
                font-size: 0.9em; 
                padding: 3px 8px; 
                border-radius: 4px; 
                margin-left: 10px; 
            }
            .privacy-public { 
                background: #e3f2fd; 
                color: #1565c0; 
            }
            .privacy-private { 
                background: #fce4ec; 
                color: #c2185b; 
            }
            
        /* Mobile Responsive Styles */
        @media (max-width: 768px) {
            header {
                flex-direction: column;
                align-items: stretch !important;
                padding: 10px !important;
            }
            
            header h1 {
                text-align: center;
                margin-bottom: 5px !important;
            }
            
            .user-menu-container {
                position: absolute !important;
                top: 10px;
                right: 10px;
            }
            
            .search-wrapper {
                order: 3 !important;
                width: 100% !important;
                margin-top: 5px;
            }
            
            #search-input {
                font-size: 16px !important; /* Prevents zoom on iOS */
                padding: 12px !important;
            }
            
            /* Make modal better on mobile */
            dialog {
                width: 95% !important;
                margin: 10px auto !important;
                padding: 15px !important;
                max-height: 90vh;
                overflow-y: auto;
            }
            
            textarea {
                font-size: 16px !important; /* Prevents zoom on iOS */
            }
            
            .privacy-toggle {
                flex-direction: column;
                gap: 10px !important;
            }
            
            .modal-buttons {
                flex-wrap: wrap;
            }
            
            .modal-buttons button {
                flex: 1;
                min-width: 120px;
            }
            
            /* Make popups better on mobile */
            .mapboxgl-popup-content {
                max-width: 250px !important;
                padding: 12px !important;
                font-size: 14px;
            }
            
            .mapboxgl-popup-close-button {
                font-size: 20px !important;
                padding: 5px 10px !important;
            }
            
            /* Better touch targets */
            button, 
            .edit-note-btn,
            .search-result-item,
            .user-trigger {
                min-height: 44px; /* Apple's recommended minimum */
                min-width: 44px;
            }
            
            /* Adjust locate button position */
            .mapboxgl-ctrl-top-left {
                top: 70px !important;
            }
            
            /* Better search results on mobile */
            #search-results {
                max-height: 50vh !important;
                font-size: 16px;
            }
            
            .search-result-item {
                padding: 15px !important;
            }
        }

        /* Small phones */
        @media (max-width: 480px) {
            header h1 {
                font-size: 1.2rem !important;
            }
            
            .user-trigger {
                font-size: 0.9rem !important;
                padding: 6px 8px !important;
            }
            
            .mapboxgl-ctrl-top-left {
                top: 80px !important;
            }
            
            .mapboxgl-ctrl-group {
                margin: 5px !important;
            }
        }

            /* Temporary marker for editing location */
            .temp-marker {
                opacity: 0.7;
                filter: grayscale(100%);
                transition: opacity 0.3s;
            }

            .temp-marker:hover {
                opacity: 1;
            }

            /* Editing mode indicator */
            .editing-location-active {
                cursor: crosshair !important;
            }

            .location-edit-controls {
                margin-top: 10px;
                padding: 10px;
                background: #f5f5f5;
                border-radius: 4px;
                display: flex;
                gap: 10px;
                justify-content: center;
            }

            .location-edit-btn {
                background: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }

            .location-edit-btn:hover {
                background: #1976D2;
            }

            .location-edit-btn.cancel {
                background: #f44336;
            }

            .location-edit-btn.cancel:hover {
                background: #d32f2f;
            }

            .location-edit-btn.save {
                background: #4CAF50;
            }

            .location-edit-btn.save:hover {
                background: #388E3C;
            }
        </style>
    </head>
    <body>
        <header style="
            padding: 10px 15px;
            background: #f0f4f8;
            border-bottom: 1px solid #ccc;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            position: relative;
            z-index: 1000;
        ">
            <!-- Search Bar - takes remaining space but not full width -->
            <div style="flex: 1; min-width: 0; max-width: calc(100% - 60px);">
                <div id="search-container" style="position: relative; width: 100%;">
                    <input type="text" 
                           id="search-input" 
                           placeholder="🔍 Search places or notes..." 
                           style="width: 100%; 
                                  padding: 10px 15px; 
                                  border: 2px solid #ddd; 
                                  border-radius: 25px; 
                                  font-size: 16px;
                                  outline: none;
                                  box-sizing: border-box;">
                    <div id="search-results" style="
                        position: absolute;
                        top: 100%;
                        left: 0;
                        right: 0;
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        margin-top: 5px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        max-height: 300px;
                        overflow-y: auto;
                        display: none;
                        z-index: 1000;
                    "></div>
                </div>
            </div>
            
            <!-- User Menu - fixed width -->
            <div class="user-menu-container" style="position: relative; flex-shrink: 0;">
                <button class="user-trigger" id="userTrigger" style="
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    padding: 8px 12px;
                    border-radius: 50%;
                    width: 44px;
                    height: 44px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                ">☰</button>
                <div class="user-dropdown" id="userDropdown">
                    <div class="user-info">
                        <div class="username">{{ current_user.username }}</div>
                        <div class="email">Signed in</div>
                    </div>
                    <a href="{{ url_for('logout') }}" class="logout">🚪 Logout</a>
                </div>
            </div>
        </header>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ 'success' if category=='success' else 'error' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div id="map-container">
            <div id="map"></div>
        </div>

        <!-- Note creation modal (unchanged) -->
        <dialog id="noteModal">
            <div class="modal-header">Add New Note</div>
            <textarea id="noteText" placeholder="Write your note here..." required></textarea>
            <div class="privacy-toggle">
                <label><input type="radio" name="privacy" value="private" checked> Private (only you)</label>
                <label><input type="radio" name="privacy" value="public"> Public (visible to everyone)</label>
            </div>
            <div class="modal-buttons">
                <button id="cancelNote">Cancel</button>
                <button id="saveNote">Save Note</button>
            </div>
        </dialog>

        <script>
// Wrap EVERYTHING in one IIFE
(function(global) {
    // ===========================================
    // All declarations at the very top
    // ===========================================
    var lastLoadedBounds = null;
    var isLoadingViewport = false;
    var loadTimer = null;
    var mapReady = false;
    
    const VIEWPORT_CONFIG = {
        LOAD_DELAY: 50,
        BUFFER_SIZE: 0.5,
        MAX_NOTES: 100
    };

    // Search variables
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    let searchTimeout;
    let currentSearchQuery = '';
    let markers = [];
    let lastSearchResults = [];

    // location edit
    let isNewNoteLocationEdit = false;

    // Track if we've already panned to user location on first load
    let hasPannedToUser = false;

    // Safe way to check if target is an element
    function isElement(obj) {
        return obj && obj.nodeType === 1; // 1 = element node
    }

    // ===========================================
    // Create the map
    // ===========================================
    mapboxgl.accessToken = 'replace_with_your_own_mapbox_token_and_thanks_for_helping';
    
    const map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [0, 0],
        zoom: 2,
        pitch: 30,
        bearing: 0,
        attributionControl: false
    });

    // ────────────────────────────────────────────────
    // Floating Action Buttons (mobile + desktop friendly)
    // ────────────────────────────────────────────────

    function addFloatingControls() {
        // New Note button (bottom right)
        const newNoteBtn = document.createElement('button');
        newNoteBtn.innerHTML = '📝';
        newNoteBtn.title = 'Add new note here';
        newNoteBtn.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: #FF5722;
            color: white;
            border: none;
            font-size: 28px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            cursor: pointer;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        `;

        newNoteBtn.addEventListener('click', () => {
            // Simulate a map click in the center of current view
            const center = map.getCenter();
            clickLat = center.lat;
            clickLng = center.lng;

            document.getElementById('noteModal').querySelector('.modal-header').textContent = 'Add New Note';
            document.getElementById('noteText').value = '';
            document.querySelector('input[name="privacy"][value="private"]').checked = true;
            setupDynamicTextarea(document.getElementById('noteText'));

            const modalButtons = document.querySelector('.modal-buttons');
            if (document.getElementById('changeLocationBtn')) {
                document.getElementById('changeLocationBtn').remove();
            }

            document.getElementById('noteModal').showModal();
        });

        // Hover/touch feedback
        newNoteBtn.addEventListener('mouseenter', () => {
            newNoteBtn.style.transform = 'scale(1.1)';
        });
        newNoteBtn.addEventListener('mouseleave', () => {
            newNoteBtn.style.transform = 'scale(1)';
        });

        document.body.appendChild(newNoteBtn);


        // Move style control to bottom-left (if you want to keep using your custom StyleControl)
        // Alternative: just change the position in CSS instead of control position
        const styleContainer = document.querySelector('.mapboxgl-ctrl-bottom-left');
        if (styleContainer) {
            styleContainer.style.cssText = `
                position: fixed !important;
                bottom: 90px !important;   /* above the new-note button */
                left: 24px !important;
                right: auto !important;
                z-index: 999;
            `;
        }
    }

    // Call it after map is loaded
    map.on('load', () => {
        console.log('Map loaded → adding floating controls');
        initViewportLoader();
        addFloatingControls();
    });

    // User menu dropdown functionality - CLEAN VERSION
    const userTrigger = document.getElementById('userTrigger');
    const userDropdown = document.getElementById('userDropdown');

    if (userTrigger && userDropdown) {
        console.log('✅ User menu elements found');
        
        // Remove any existing handlers by cloning and replacing (prevents duplicates)
        const newUserTrigger = userTrigger.cloneNode(true);
        userTrigger.parentNode.replaceChild(newUserTrigger, userTrigger);
        
        // Use the new element
        const finalUserTrigger = newUserTrigger;
        const finalUserDropdown = userDropdown;
        
        // Toggle menu on click
        finalUserTrigger.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('🍔 Menu clicked - toggling dropdown');
            
            // Toggle display
            if (finalUserDropdown.style.display === 'block') {
                finalUserDropdown.style.display = 'none';
            } else {
                finalUserDropdown.style.display = 'block';
            }
        });

        // Close when clicking outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.user-menu-container')) {
                if (finalUserDropdown.style.display === 'block') {
                    console.log('👆 Click outside - closing menu');
                    finalUserDropdown.style.display = 'none';
                }
            }
        });

        // Close on scroll (for mobile)
        window.addEventListener('scroll', function() {
            if (finalUserDropdown.style.display === 'block') {
                finalUserDropdown.style.display = 'none';
            }
        }, { passive: true });
        
    } else {
        console.error('❌ User menu elements not found');
    }


    // ===========================================
    // Define ALL helper functions
    // ===========================================
    
    // Convert distance to human-readable description
    function getDistanceDescription(distance) {
        if (distance < 0.1) return "📍 right here";
        if (distance < 0.5) return "🚶 very nearby";
        if (distance < 1) return "👣 nearby";
        if (distance < 3) return "🚶‍♂️ a short walk away";
        if (distance < 5) return "🚲 a few kilometers away";
        if (distance < 10) return "🚗 within the area";
        if (distance < 30) return "🚙 further out";
        if (distance < 100) return "🛣 far away";
        if (distance < 500) return "✈️ very far away";
        return "🌍 extremely far away";
    }

    // Format distance nicely
    function formatDistance(distance) {
        if (distance < 1) {
            return `${Math.round(distance * 1000)} m`;
        } else if (distance < 10) {
            return `${distance.toFixed(1)} km`;
        } else {
            return `${Math.round(distance)} km`;
        }
    }

    // Helper function to calculate distance between two coordinates in km
    function calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = 
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
            Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

// Create marker from note
    function createMarkerFromNote(note, currentLat, currentLng) {
        const privacyClass = note.privacy === 'public' ? 'privacy-public' : 'privacy-private';
        const privacyLabel = note.privacy === 'public' ? 'Public' : 'Private';

        let timeInfo = '';
        if (note.created_at) {
            const created = new Date(note.created_at);
            timeInfo = `Posted ${created.toLocaleString()}`;
            if (note.updated_at && note.updated_at !== note.created_at) {
                const updated = new Date(note.updated_at);
                timeInfo += ` • Edited ${updated.toLocaleString()}`;
            }
        }
        
        // Build location info string
        let locationInfo = '';

        // Show distance from current location (prioritize this)
        if (currentLat && currentLng) {
            const distance = calculateDistance(
                currentLat, currentLng,
                note.lat, note.lng
            );
            const description = getDistanceDescription(distance);
            locationInfo = ` ${description}`;
        } 
        // Only show creation distance if current location isn't available
        else if (note.user_lat && note.user_lng) {
            const fromWhereDistance = calculateDistance(
                note.user_lat, note.user_lng,
                note.lat, note.lng
            );
            const description = getDistanceDescription(fromWhereDistance);
            locationInfo = ` from ${description}`;
        }

        let addressInfo = '';
        if (note.address) {
            addressInfo = `<div style="font-size: 11px; color: #666; margin-top: 5px;">📍 ${note.address}</div>`;
        }

        const text = String(note?.text ?? '');
        const escapedText = text.replace(/[&<>"']/g, (char) => ({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#39;'
        }[char]));

        const htmlText = escapedText.replace(/\\n/g, '<br>').replace(/\\r/g, '');
        const textSizeClass = getTextSizeClass(note.text);

        let popupContent = `
            <strong class="note-user">${note.username}</strong>
            <span class="note-privacy ${privacyClass}">${privacyLabel}</span></br>
            ${locationInfo ? `<span style="font-size: 12px; color: #666; margin-left: 8px;">${locationInfo}</span>` : ''}
            <br>
            <div class="note-text ${textSizeClass}">${htmlText}</div>
            ${addressInfo}
            <small>${timeInfo}</small>
        `;

        if (note.is_owner) {
            const escapedAttrText = note.text
                .replace(/&/g, '&amp;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            popupContent += `
                <br>
                <button 
                  class="edit-note-btn"
                  data-id="${note.id}"
                  data-lat="${note.lat}"
                  data-lng="${note.lng}"
                  data-text="${escapedAttrText}"
                  data-privacy="${note.privacy}">
                  Edit Note
                </button>
            `;
        }

        const popup = new mapboxgl.Popup({ offset: 25 })
            .setHTML(popupContent);

        const marker = new mapboxgl.Marker()
            .setLngLat([note.lng, note.lat])
            .setPopup(popup)
            .addTo(map);

        marker.noteId = note.id;
        markers.push(marker);
    }

    function updateExistingPopup(noteId, updatedNote) {
        const marker = markers.find(m => m.noteId === noteId);
        if (!marker) return;

        const popup = marker.getPopup();
        if (!popup.isOpen()) return;  // only update if it's currently open

        // Re-build the content exactly like in createMarkerFromNote
        const privacyClass = updatedNote.privacy === 'public' ? 'privacy-public' : 'privacy-private';
        const privacyLabel = updatedNote.privacy === 'public' ? 'Public' : 'Private';

        let timeInfo = `Posted ${new Date(updatedNote.created_at).toLocaleString()}`;
        if (updatedNote.updated_at && updatedNote.updated_at !== updatedNote.created_at) {
            timeInfo += ` • Edited ${new Date(updatedNote.updated_at).toLocaleString()}`;
        }

        const locationInfo = ''; // you can re-calculate distance if you want
        const escapedText = String(updatedNote.text ?? '')
            .replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
        const htmlText = escapedText.replace(/\\n/g, '<br>');

        const textSizeClass = getTextSizeClass(updatedNote.text);

        let newContent = `
            <strong class="note-user">${updatedNote.username}</strong>
            <span class="note-privacy ${privacyClass}">${privacyLabel}</span><br>
            ${locationInfo ? `<span style="font-size:12px;color:#666;margin-left:8px;">${locationInfo}</span>` : ''}
            <br>
            <div class="note-text ${textSizeClass}">${htmlText}</div>
            ${updatedNote.address ? `<div style="font-size:11px;color:#666;margin-top:5px;">📍 ${updatedNote.address}</div>` : ''}
            <small>${timeInfo}</small>
        `;

        if (updatedNote.is_owner) {
            const escapedAttr = updatedNote.text
                .replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')
                .replace(/</g,'&lt;').replace(/>/g,'&gt;');

            newContent += `
                <br>
                <button class="edit-note-btn"
                        data-id="${updatedNote.id}"
                        data-lat="${updatedNote.lat}"
                        data-lng="${updatedNote.lng}"
                        data-text="${escapedAttr}"
                        data-privacy="${updatedNote.privacy}">
                    Edit Note
                </button>
            `;
        }

        popup.setHTML(newContent);

        // Optional: re-attach edit button listener if needed (delegation should still work)
    }

    // Helper to clear all markers
    function clearAllMarkers() {
        markers.forEach(marker => marker.remove());
        markers = [];
    }

    // Update search result count
    function updateSearchResultCount(count) {
        let countDiv = document.getElementById('search-result-count');
        
        if (!countDiv && count > 0) {
            countDiv = document.createElement('div');
            countDiv.id = 'search-result-count';
            countDiv.style.padding = '8px 15px';
            countDiv.style.background = '#f0f0f0';
            countDiv.style.fontSize = '12px';
            countDiv.style.color = '#666';
            countDiv.style.borderBottom = '1px solid #ddd';
            searchResults.insertBefore(countDiv, searchResults.firstChild);
        }
        
        if (countDiv) {
            countDiv.textContent = `📌 ${count} notes match your search`;
        }
    }

    // Refresh markers with search filter
    function refreshMarkers(notes, currentLat = null, currentLng = null) {
        // Check if notes is an array, if not, try to extract notes from response
        let notesArray = notes;
        if (!Array.isArray(notes)) {
            // If it's a response object with a notes property (like your API returns)
            if (notes && notes.notes && Array.isArray(notes.notes)) {
                notesArray = notes.notes;
            } else {
                console.error('Expected array of notes but got:', notes);
                return;
            }
        }
        
        const filteredNotes = notesArray.filter(note => {
            if (!currentSearchQuery || currentSearchQuery.length < 2) return true;
            
            const query = currentSearchQuery.toLowerCase();
            const searchableText = `
                ${note.text || ''} 
                ${note.username || ''} 
                ${note.address || ''} 
                ${note.place_name || ''} 
                ${note.country || ''}
            `.toLowerCase();
            
            return searchableText.includes(query);
        });

        filteredNotes.forEach(note => {
            const existingMarker = markers.find(m => m.noteId === note.id);
            
            if (!existingMarker) {
                createMarkerFromNote(note, currentLat, currentLng);
            }
        });
        
        updateSearchResultCount(filteredNotes.length);
    }

    // ===========================================
    // CLICK-HOLD ONLY - IMPROVED VERSION
    // ===========================================

    let pressTimer;
    let isLongPress = false;
    let pressStartTime;
    let pressLocation = null;
    let pressStarted = false;
    let dragDetected = false;

    // For desktop - mouse down
    map.on('mousedown', function(e) {
        // Don't start press if clicking on marker or popup
        if (e.originalEvent.target.closest('.mapboxgl-marker') || 
            e.originalEvent.target.closest('.mapboxgl-popup') ||
            editingNote) {
            return;
        }
        
        console.log('Mouse down - starting timer');
        pressStarted = true;
        dragDetected = false;
        pressLocation = {
            lat: e.lngLat.lat,
            lng: e.lngLat.lng
        };
        
        pressStartTime = Date.now();
        isLongPress = false;
        
        // Set timer for long press
        pressTimer = setTimeout(() => {
            if (pressStarted && !dragDetected) {
                isLongPress = true;
                
                console.log('📍 Long press detected - opening new note modal');
                
                clickLat = pressLocation.lat;
                clickLng = pressLocation.lng;
                
                // Reset editing state
                editingNote = null;
                isEditingLocation = false;
                isNewNoteLocationEdit = false;
                
                // Prepare and show modal
                document.getElementById('noteModal').querySelector('.modal-header').textContent = 'Add New Note';
                document.getElementById('noteText').value = '';
                document.querySelector('input[name="privacy"][value="private"]').checked = true;
                
                setupDynamicTextarea(document.getElementById('noteText'));
                
                const existingBtn = document.getElementById('changeLocationBtn');
                if (existingBtn) existingBtn.remove();
                
                document.getElementById('noteModal').showModal();
                
                // Add change location button
                const modalButtons = document.querySelector('.modal-buttons');
                if (!document.getElementById('changeLocationBtn')) {
                    const changeLocationBtn = document.createElement('button');
                    changeLocationBtn.id = 'changeLocationBtn';
                    changeLocationBtn.textContent = '📍 Change Location';
                    changeLocationBtn.style.background = '#FF9800';
                    changeLocationBtn.style.color = 'white';
                    changeLocationBtn.style.marginRight = 'auto';
                    changeLocationBtn.style.border = 'none';
                    changeLocationBtn.style.padding = '10px 18px';
                    changeLocationBtn.style.borderRadius = '4px';
                    changeLocationBtn.style.cursor = 'pointer';
                    
                    changeLocationBtn.onclick = startNewNoteLocationEdit;
                    
                    modalButtons.insertBefore(changeLocationBtn, modalButtons.firstChild);
                }
            }
        }, 500);
    });

    // For mobile - touch start
    map.on('touchstart', function(e) {
        if (e.originalEvent.target.closest('.mapboxgl-marker') || 
            e.originalEvent.target.closest('.mapboxgl-popup') ||
            editingNote) {
            return;
        }
        
        console.log('Touch start - starting timer');
        pressStarted = true;
        dragDetected = false;
        pressLocation = {
            lat: e.lngLat.lat,
            lng: e.lngLat.lng
        };
        
        pressStartTime = Date.now();
        isLongPress = false;
        
        pressTimer = setTimeout(() => {
            if (pressStarted && !dragDetected) {
                isLongPress = true;
                
                console.log('📍 Long press detected - opening new note modal');
                
                clickLat = pressLocation.lat;
                clickLng = pressLocation.lng;
                
                editingNote = null;
                isEditingLocation = false;
                isNewNoteLocationEdit = false;
                
                document.getElementById('noteModal').querySelector('.modal-header').textContent = 'Add New Note';
                document.getElementById('noteText').value = '';
                document.querySelector('input[name="privacy"][value="private"]').checked = true;
                
                setupDynamicTextarea(document.getElementById('noteText'));
                
                const existingBtn = document.getElementById('changeLocationBtn');
                if (existingBtn) existingBtn.remove();
                
                document.getElementById('noteModal').showModal();
                
                const modalButtons = document.querySelector('.modal-buttons');
                if (!document.getElementById('changeLocationBtn')) {
                    const changeLocationBtn = document.createElement('button');
                    changeLocationBtn.id = 'changeLocationBtn';
                    changeLocationBtn.textContent = '📍 Change Location';
                    changeLocationBtn.style.background = '#FF9800';
                    changeLocationBtn.style.color = 'white';
                    changeLocationBtn.style.marginRight = 'auto';
                    changeLocationBtn.style.border = 'none';
                    changeLocationBtn.style.padding = '10px 18px';
                    changeLocationBtn.style.borderRadius = '4px';
                    changeLocationBtn.style.cursor = 'pointer';
                    
                    changeLocationBtn.onclick = startNewNoteLocationEdit;
                    
                    modalButtons.insertBefore(changeLocationBtn, modalButtons.firstChild);
                }
            }
        }, 500);
    });

    // Detect drag start
    map.on('dragstart', function() {
        console.log('Drag detected - cancelling long press');
        dragDetected = true;
        pressStarted = false;
        clearTimeout(pressTimer);
    });

    // Also detect movement
    map.on('mousemove', function() {
        if (pressStarted) {
            dragDetected = true;
            pressStarted = false;
            clearTimeout(pressTimer);
        }
    });

    map.on('touchmove', function() {
        if (pressStarted) {
            dragDetected = true;
            pressStarted = false;
            clearTimeout(pressTimer);
        }
    });

    // For desktop - mouse up
    map.on('mouseup', function(e) {
        clearTimeout(pressTimer);
        const pressDuration = Date.now() - pressStartTime;
        
        if (!isLongPress && pressDuration < 500 && pressStarted && !dragDetected) {
            console.log('Short click - ignored');
        }
        
        pressStarted = false;
        pressLocation = null;
    });

    // For mobile - touch end
    map.on('touchend', function(e) {
        clearTimeout(pressTimer);
        const pressDuration = Date.now() - pressStartTime;
        
        if (!isLongPress && pressDuration < 500 && pressStarted && !dragDetected) {
            console.log('Short tap - ignored');
        }
        
        pressStarted = false;
        pressLocation = null;
    });

    // Cancel if mouse leaves map during press
    map.on('mouseleave', function() {
        clearTimeout(pressTimer);
        pressStarted = false;
        pressLocation = null;
        isLongPress = false;
        dragDetected = false;
    });

    map.on('touchcancel', function() {
        clearTimeout(pressTimer);
        pressStarted = false;
        pressLocation = null;
        isLongPress = false;
        dragDetected = false;
    });

    // Remove any existing click handlers
    map.off('click');

    // ===========================================
    // Viewport loading functions
    // ===========================================
    

    async function loadViewportNotes() {
        if (!mapReady || !map || !map.loaded) {
            console.log('Map not ready');
            return;
        }
        
        if (typeof map.loaded === 'function' && !map.loaded()) {
            console.log('Map not fully loaded');
            return;
        }
        
        if (isLoadingViewport) return;
        
        try {
            const bounds = map.getBounds();
            const sw = bounds.getSouthWest();
            const ne = bounds.getNorthEast();
            
            const latBuffer = (ne.lat - sw.lat) * VIEWPORT_CONFIG.BUFFER_SIZE;
            const lngBuffer = (ne.lng - sw.lng) * VIEWPORT_CONFIG.BUFFER_SIZE;
            
            const boundsParam = `${sw.lat - latBuffer},${sw.lng - lngBuffer},${ne.lat + latBuffer},${ne.lng + lngBuffer}`;
            
            if (lastLoadedBounds === boundsParam) return;
            lastLoadedBounds = boundsParam;
            
            isLoadingViewport = true;
            
            var currentLat = null, currentLng = null;
            if (navigator.geolocation && global.userLat) {
                currentLat = global.userLat;
                currentLng = global.userLng;
            }
            
            const response = await fetch(`/get_notes_in_view?bounds=${encodeURIComponent(boundsParam)}&limit=${VIEWPORT_CONFIG.MAX_NOTES}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const notes = await response.json();
            
            notes.forEach(note => {
                const exists = markers.some(m => m.noteId === note.id);
                if (!exists) {
                    createMarkerFromNote(note, currentLat, currentLng);
                }
            });
            
        } catch (error) {
            console.error('Failed to load viewport notes:', error);
        } finally {
            isLoadingViewport = false;
        }
    }

    function setupViewportEvents() {
        console.log('Setting up viewport events');
        
        setTimeout(() => {
            if (map && map.loaded()) {
                loadViewportNotes();
            }
        }, 1000);
        
        map.on('moveend', () => {
            if (loadTimer) clearTimeout(loadTimer);
            loadTimer = setTimeout(() => {
                if (map && map.loaded()) {
                    loadViewportNotes();
                }
            }, VIEWPORT_CONFIG.LOAD_DELAY);
        });
        
        map.on('zoomend', () => {
            if (loadTimer) clearTimeout(loadTimer);
            loadTimer = setTimeout(() => {
                if (map && map.loaded()) {
                    loadViewportNotes();
                }
            }, VIEWPORT_CONFIG.LOAD_DELAY);
        });
    }

    function initViewportLoader() {
        console.log('Initializing viewport loader');
        
        if (!map || typeof map.loaded !== 'function') {
            console.log('Map not properly initialized');
            return;
        }
        
        mapReady = true;
        
        if (map.loaded()) {
            setupViewportEvents();
        } else {
            map.once('load', setupViewportEvents);
        }
    }

    // Dynamic text size

    // Calculate appropriate text size based on content length
    function getTextSizeClass(text) {
        const length = text?.length || 0;
        
        if (length < 50) return 'text-size-xxl';      // Very short: 24px
        if (length < 100) return 'text-size-xl';       // Short: 20px
        if (length < 200) return 'text-size-lg';       // Medium-short: 18px
        if (length < 500) return 'text-size-md';       // Medium: 16px
        if (length < 1000) return 'text-size-sm';      // Medium-long: 14px
        return 'text-size-xs';                           // Long: 12px
    }

    // Make it globally available for testing
    window.getTextSizeClass = getTextSizeClass;

    // Apply dynamic sizing to text in popups
    function applyDynamicSizing(element, text) {
        element.classList.add('dynamic-text');
        element.classList.add(getTextSizeClass(text));
    }

    // For textareas (live as you type)
    function setupDynamicTextarea(textarea) {
        textarea.classList.add('dynamic-textarea');
        
        function updateSize() {
            const text = textarea.value;
            // Remove existing size classes
            textarea.classList.remove('text-size-xxl', 'text-size-xl', 'text-size-lg', 
                                      'text-size-md', 'text-size-sm', 'text-size-xs');
            // Add new size class
            textarea.classList.add(getTextSizeClass(text));
            
            // Auto-adjust height
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(400, Math.max(100, textarea.scrollHeight)) + 'px';
        }
        
        // Update on input
        textarea.addEventListener('input', updateSize);
        
        // Initial update
        updateSize();
    }


    // ===========================================
    // Load notes function - NO AUTO-PANNING
    // ===========================================

    // Helper function to add user location dot (with duplicate prevention)
    let userLocationMarker = null;

    function addUserLocationDot(lat, lng) {
        // Remove existing user location marker if it exists
        if (userLocationMarker) {
            userLocationMarker.remove();
        }
        
        // Add CSS animation for pulsing effect if not already added
        if (!document.getElementById('pulse-style')) {
            const style = document.createElement('style');
            style.id = 'pulse-style';
            style.textContent = `
                @keyframes pulse {
                    0% { box-shadow: 0 0 0 0 rgba(66, 133, 244, 0.7); }
                    70% { box-shadow: 0 0 0 15px rgba(66, 133, 244, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(66, 133, 244, 0); }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Create pulsing dot for user location
        const dot = document.createElement('div');
        dot.style.width = '20px';
        dot.style.height = '20px';
        dot.style.background = '#4285F4';
        dot.style.border = '3px solid white';
        dot.style.borderRadius = '50%';
        dot.style.boxShadow = '0 0 10px rgba(66, 133, 244, 0.8)';
        dot.style.animation = 'pulse 1.5s infinite';
        
        // Add the marker to the map and store reference
        userLocationMarker = new mapboxgl.Marker({ element: dot })
            .setLngLat([lng, lat])
            .setPopup(new mapboxgl.Popup({ offset: 25 })
                .setHTML('<strong>📍 You are here!</strong>'))
            .addTo(map);
    }

    function loadNotes() {
        // Store user location globally
        if (navigator.geolocation) {
            console.log('Requesting user location...');
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    window.userLat = position.coords.latitude;
                    window.userLng = position.coords.longitude;
                    console.log('📍 Got user location:', window.userLat, window.userLng);
                    
                    // Add user location dot
                    addUserLocationDot(window.userLat, window.userLng);
                    
                    // PAN TO LOCATION ON FIRST LOAD ONLY
                    if (!hasPannedToUser) {
                        console.log('📍 First load - panning to user location');
                        map.flyTo({
                            center: [window.userLng, window.userLat],
                            zoom: 14,
                            essential: true,
                            pitch: 45,
                            duration: 3000
                        });
                        hasPannedToUser = true;
                    }
                    
                    // Load notes with location (for distance calculations)
                    fetchAndDisplayNotes(window.userLat, window.userLng);
                },
                (error) => {
                    console.log('Could not get user location:', error.message);
                    window.userLat = null;
                    window.userLng = null;
                    fetchAndDisplayNotes();
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        } else {
            console.log('Geolocation not supported');
            window.userLat = null;
            window.userLng = null;
            fetchAndDisplayNotes();
        }
    }

    // Separate function to fetch and display notes
    function fetchAndDisplayNotes(currentLat = null, currentLng = null) {
        fetch('/get_notes')
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then(notes => {
                clearAllMarkers();
                refreshMarkers(notes, currentLat, currentLng);
            })
            .catch(err => {
                console.error('Failed to load notes:', err);
                alert('Could not load notes – check connection or server logs');
            });
    }

    // ===========================================
    // Search functions
    // ===========================================
    
    function performSearch(query) {
        currentSearchQuery = query;
        
        searchResults.innerHTML = '<div style="padding: 10px; text-align: center;">Searching...</div>';
        searchResults.style.display = 'block';
        
        const isLocationSearch = /[a-zA-Z]/.test(query) && query.length > 2;
        
        fetch(`/search?q=${encodeURIComponent(query)}&location=${isLocationSearch}`)
            .then(r => r.json())
            .then(data => {
                displaySearchResults(data);
                
                fetch(`/get_notes?q=${encodeURIComponent(query)}&all=true`)
                    .then(r => r.json())
                    .then(notesData => {
                        if (navigator.geolocation) {
                            navigator.geolocation.getCurrentPosition(
                                (position) => {
                                    clearAllMarkers();
                                    notesData.notes.forEach(note => {
                                        createMarkerFromNote(note, position.coords.latitude, position.coords.longitude);
                                    });
                                    updateSearchResultCount(notesData.notes.length);
                                },
                                () => {
                                    clearAllMarkers();
                                    notesData.notes.forEach(note => {
                                        createMarkerFromNote(note);
                                    });
                                    updateSearchResultCount(notesData.notes.length);
                                }
                            );
                        } else {
                            clearAllMarkers();
                            notesData.notes.forEach(note => {
                                createMarkerFromNote(note);
                            });
                            updateSearchResultCount(notesData.notes.length);
                        }
                    });
            })
            .catch(err => {
                console.error('Search failed:', err);
                searchResults.innerHTML = '<div style="padding: 10px; color: red;">Search failed</div>';
            });
    }

    function displaySearchResults(results) {
        if (!results || results.length === 0) {
            searchResults.innerHTML = '<div style="padding: 10px; text-align: center;">No results found</div>';
            return;
        }
        
        lastSearchResults = results;
        
        const bounds = map.getBounds();
        const center = map.getCenter();
        
        const resultsWithDistance = results.map(result => {
            const distance = calculateDistance(
                center.lat, center.lng,
                result.lat, result.lng
            );
            return { ...result, distance };
        });
        
        resultsWithDistance.sort((a, b) => a.distance - b.distance);
        
        const nearestResult = resultsWithDistance[0];
        
        if (nearestResult && (nearestResult.distance > 1 || !bounds.contains([nearestResult.lat, nearestResult.lng]))) {
            map.flyTo({
                center: [nearestResult.lng, nearestResult.lat],
                zoom: Math.max(map.getZoom(), 12),
                duration: 1500,
                essential: false
            });
        }
        
        let html = '';
        resultsWithDistance.forEach(result => {
            const icon = result.type === 'location' ? '📍' : '📝';
            const distanceStr = result.distance < 0.1 ? 'Very close' : 
                               result.distance < 1 ? `${Math.round(result.distance * 1000)}m away` :
                               `${result.distance.toFixed(1)}km away`;
            
            html += `
                <div class="search-result-item" 
                     onclick="selectSearchResult('${result.id}', ${result.lat}, ${result.lng})"
                     style="padding: 12px 15px; 
                            border-bottom: 1px solid #eee;
                            cursor: pointer;
                            transition: background 0.2s;
                            display: flex;
                            align-items: center;
                            gap: 10px;">
                    <span style="font-size: 18px;">${icon}</span>
                    <div style="flex: 1;">
                        <div style="font-weight: bold; display: flex; justify-content: space-between;">
                            <span>${result.title}</span>
                            <span style="font-size: 11px; color: #666; font-weight: normal;">${distanceStr}</span>
                        </div>
                        <div style="font-size: 12px; color: #666;">${result.subtitle || ''}</div>
                    </div>
                </div>
            `;
        });
        
        if (resultsWithDistance.length > 1) {
            html += `
                <div style="padding: 10px; text-align: center; border-top: 1px solid #eee;">
                    <button onclick="showAllResults()" style="
                        background: none;
                        border: none;
                        color: #2196F3;
                        cursor: pointer;
                        font-size: 12px;
                        padding: 8px 12px;
                        width: 100%;
                        transition: background 0.2s;
                        border-radius: 0 0 4px 4px;
                    " onmouseover="this.style.background='#f0f0f0'" onmouseout="this.style.background='none'">
                        🗺️ Show all ${resultsWithDistance.length} results on map
                    </button>
                </div>
            `;
        }
        
        searchResults.innerHTML = html;
        
        document.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('mouseenter', () => {
                item.style.background = '#f5f5f5';
            });
            item.addEventListener('mouseleave', () => {
                item.style.background = 'white';
            });
        });
        
        if (resultsWithDistance.length > 0) {
            const nearestIndicator = document.createElement('div');
            nearestIndicator.style.padding = '8px 15px';
            nearestIndicator.style.background = '#e3f2fd';
            nearestIndicator.style.fontSize = '12px';
            nearestIndicator.style.color = '#1565c0';
            nearestIndicator.style.borderBottom = '1px solid #bbdefb';
            nearestIndicator.style.display = 'flex';
            nearestIndicator.style.alignItems = 'center';
            nearestIndicator.style.gap = '5px';
            nearestIndicator.innerHTML = `
                <span style="font-size: 14px;">🎯</span>
                <span>Panned to nearest result • ${results.length} total</span>
            `;
            
            searchResults.insertBefore(nearestIndicator, searchResults.firstChild);
        }
    }

    function showAllResults() {
        if (!lastSearchResults || lastSearchResults.length === 0) return;
        
        const bounds = new mapboxgl.LngLatBounds();
        lastSearchResults.forEach(result => {
            bounds.extend([result.lng, result.lat]);
        });
        
        map.fitBounds(bounds, {
            padding: 50,
            duration: 2000
        });
        
        searchResults.style.display = 'none';
    }

    // Make showAllResults globally available
    window.showAllResults = showAllResults;


    function selectSearchResult(id, lat, lng) {
    map.flyTo({
        center: [lng, lat],
        zoom: 14,
        essential: true,
        pitch: 45,
        duration: 2000
    });
    
    searchResults.style.display = 'none';
    searchInput.focus();
    
    if (id.toString().startsWith('note_')) {
        const noteId = parseInt(id.replace('note_', ''));
        const marker = markers.find(m => m.noteId === noteId);
        if (marker) {
            marker.togglePopup();
            
            const markerElement = marker.getElement();
            if (markerElement) {
                markerElement.style.transition = 'transform 0.3s, box-shadow 0.3s';
                markerElement.style.transform = 'scale(1.2)';
                markerElement.style.boxShadow = '0 0 20px rgba(33, 150, 243, 0.8)';
                markerElement.style.zIndex = '1000';
                
                setTimeout(() => {
                    markerElement.style.transform = '';
                    markerElement.style.boxShadow = '';
                    markerElement.style.zIndex = '';
                }, 2000);
            }
            
            setTimeout(() => marker.togglePopup(), 3000);
        }
    }
}

// Make selectSearchResult globally available
window.selectSearchResult = selectSearchResult;

    // ===========================================
    // Initialize everything
    // ===========================================
    
    // Store user location globally
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                global.userLat = position.coords.latitude;
                global.userLng = position.coords.longitude;
            },
            (error) => {
                console.log('Could not get user location');
            }
        );
    }

    // Add map controls
    map.addControl(new mapboxgl.NavigationControl());
    map.addControl(new mapboxgl.FullscreenControl());

    // Style control
    // Style control - Compact version
    class StyleControl {
        onAdd(map) {
            this._map = map;
            this._container = document.createElement('div');
            this._container.className = 'mapboxgl-ctrl mapboxgl-ctrl-group';
            this._container.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 20px;
                z-index: 10;
                border-radius: 30px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            `;
            
            // Create a compact select
            const select = document.createElement('select');
            select.style.cssText = `
                padding: 10px 30px 10px 15px;
                border: none;
                background: white;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                outline: none;
                appearance: none;
                background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
                background-repeat: no-repeat;
                background-position: right 10px center;
                background-size: 16px;
                min-width: 150px;
            `;
            
            const styles = [
                { value: 'mapbox://styles/mapbox/streets-v12', label: '🗺️ Street' },
                { value: 'mapbox://styles/mapbox/satellite-streets-v12', label: '🛰️ Satellite' },
                { value: 'mapbox://styles/mapbox/outdoors-v12', label: '🌲 Outdoors' },
                { value: 'mapbox://styles/mapbox/light-v11', label: '☀️ Light' },
                { value: 'mapbox://styles/mapbox/dark-v11', label: '🌙 Dark' }
            ];
            
            styles.forEach(style => {
                const option = document.createElement('option');
                option.value = style.value;
                option.textContent = style.label;
                select.appendChild(option);
            });
            
            select.addEventListener('change', (e) => {
                this._map.setStyle(e.target.value);
            });
            
            this._container.appendChild(select);
            return this._container;
        }
        
        onRemove() {
            this._container.parentNode.removeChild(this._container);
            this._map = undefined;
        }
    }

    // Add the style control to bottom right
    map.addControl(new StyleControl(), 'bottom-left');

    // Locate control - update flag when manually panning
    class LocateControl {
        onAdd(map) {
            this._map = map;
            this._container = document.createElement('div');
            this._container.className = 'mapboxgl-ctrl mapboxgl-ctrl-group';
            this._container.style.margin = '10px';
            
            const button = document.createElement('button');
            button.className = 'mapboxgl-ctrl-icon';
            button.style.width = '36px';
            button.style.height = '36px';
            button.style.padding = '8px';
            button.style.cursor = 'pointer';
            button.style.background = 'white';
            button.style.border = 'none';
            button.style.borderRadius = '4px';
            button.style.display = 'flex';
            button.style.alignItems = 'center';
            button.style.justifyContent = 'center';
            button.style.fontSize = '20px';
            button.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
            button.innerHTML = '📍';
            button.title = 'Find my location';
            
            button.addEventListener('mouseenter', () => {
                button.style.background = '#f0f0f0';
            });
            button.addEventListener('mouseleave', () => {
                button.style.background = 'white';
            });
            
            button.addEventListener('click', () => {
                if (navigator.geolocation) {
                    button.style.background = '#e3f2fd';
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            // Update stored location
                            window.userLat = position.coords.latitude;
                            window.userLng = position.coords.longitude;
                            
                            // PAN to location (manual)
                            this._map.flyTo({
                                center: [window.userLng, window.userLat],
                                zoom: 14,
                                essential: true,
                                pitch: 45,
                                duration: 2000
                            });
                            
                            // Update the flag so we know we've manually panned
                            hasPannedToUser = true;
                            
                            // Update or add the user location dot
                            addUserLocationDot(window.userLat, window.userLng);
                            
                            button.style.background = 'white';
                        },
                        (error) => {
                            alert('Could not get your location. Please check your permissions.');
                            button.style.background = 'white';
                        }
                    );
                } else {
                    alert('Geolocation is not supported by your browser.');
                }
            });
            
            this._container.appendChild(button);
            return this._container;
        }
        
        onRemove() {
            this._container.parentNode.removeChild(this._container);
            this._map = undefined;
        }
    }

    setTimeout(() => {
        map.addControl(new LocateControl(), 'top-left');
    }, 1000);


    // Modal handling
    const modal = document.getElementById('noteModal');
    modal.addEventListener('toggle', function() {
        setTimeout(() => map.resize(), 100);
    });

    window.addEventListener('resize', function() {
        map.resize();
    });

    // Search input handler
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        
        const clearBtn = document.getElementById('clear-search');
        if (clearBtn) {
            clearBtn.style.display = query.length > 0 ? 'block' : 'none';
        }
        
        if (query.length < 2) {
            searchResults.style.display = 'none';
            if (currentSearchQuery !== '') {
                currentSearchQuery = '';
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            fetch('/get_notes')
                                .then(r => r.json())
                                .then(notes => {
                                    clearAllMarkers();
                                    refreshMarkers(notes, position.coords.latitude, position.coords.longitude);
                                });
                        },
                        () => {
                            fetch('/get_notes')
                                .then(r => r.json())
                                .then(notes => {
                                    clearAllMarkers();
                                    refreshMarkers(notes);
                                });
                        }
                    );
                }
            }
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    // Click outside search results
    document.addEventListener('click', function(e) {
        if (!isElement(e.target)) return;
        if (!e.target.closest('#search-container')) {
            searchResults.style.display = 'none';
        }
    });
    // Initial load
    loadNotes();

    // Initialize viewport loader
    map.on('load', () => {
        console.log('Map loaded, starting viewport loader');
        initViewportLoader();
    });

    // Edit functionality
    let editingNote = null;
    let originalLat, originalLng, originalPrivacy;
    let isEditingLocation = false;
    let tempMarker = null;
    let originalMarker = null;
    let clickLat, clickLng;




    document.addEventListener('click', function(e) {
        // ────────────────────────────────────────────────
        //   Very permissive save button detection
        // ────────────────────────────────────────────────
        if (e.target.id === 'saveNote' || e.target.closest('#saveNote')) {
            console.log("SAVE CLICK DETECTED — target:", e.target);

            e.preventDefault();
            e.stopPropagation();

            const text = document.getElementById('noteText')?.value?.trim();
            if (!text) {
                alert("Please write something");
                return;
            }

            const privacy = document.querySelector('input[name="privacy"]:checked')?.value;
            if (!privacy) {
                alert("Please choose public or private");
                return;
            }

            console.log("→ Collecting data…", { text: text.slice(0,30), privacy });

            const isNew = !editingNote;
            if (isNew && (!clickLat || !clickLng)) {
                alert("No location selected – please click the map first");
                return;
            }

            let url  = isNew ? '/add_note' : '/edit_note';
            let body = { text, privacy };

            if (!isNew) {
                body.id = editingNote.id;
                body.lat = editingNote.lat;
                body.lng = editingNote.lng;
            } else {
                body.lat = clickLat;
                body.lng = clickLng;
            }

            // Add user location if we have it
            if (window.userLat && window.userLng) {
                body.user_lat = window.userLat;
                body.user_lng = window.userLng;
            }

            console.log("→ Sending to:", url, body);

            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })
            .then(r => {
                console.log("← Server answered with status:", r.status);
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then(data => {
                console.log("← Success data:", data);
                if (data.success) {
                    // If this was an edit AND the server returned the updated note
                    if (!isNew && data.note) {
                        console.log("🔄 Updating popup for note:", editingNote.id);
                        
                        // Check if location changed - if so, we need to recreate the marker
                        const oldMarker = markers.find(m => m.noteId === editingNote.id);
                        if (oldMarker) {
                            const oldLngLat = oldMarker.getLngLat();
                            const locationChanged = 
                                oldLngLat.lat !== data.note.lat || 
                                oldLngLat.lng !== data.note.lng;
                            
                            if (locationChanged) {
                                console.log("📍 Location changed - recreating marker");
                                // Remove old marker
                                oldMarker.remove();
                                markers = markers.filter(m => m.noteId !== editingNote.id);
                                
                                // Create new marker with updated location
                                createMarkerFromNote(data.note, window.userLat, window.userLng);
                            } else {
                                // Just update the popup
                                updateExistingPopup(editingNote.id, data.note);
                            }
                        }
                    }
                    
                    document.getElementById('noteModal').close();
                    
                    // For new notes, reload all notes
                    if (isNew) {
                        loadNotes();
                    }
                    
                    editingNote = null;
                    
                    // Clean up change location button
                    const changeLocationBtn = document.getElementById('changeLocationBtn');
                    if (changeLocationBtn) changeLocationBtn.remove();
                    
                    // Clean up temp marker
                    if (tempMarker) {
                        tempMarker.remove();
                        tempMarker = null;
                    }
                    
                    // Reset location variables
                    clickLat = null;
                    clickLng = null;
                } else {
                    alert("Save failed: " + (data.error || "Unknown error"));
                }
            })
            .catch(err => {
                console.error("Save request failed:", err);
                alert("Could not save note – check console");
            });
        }
    }, false);

    function startEdit(id, lat, lng, text, privacy) {

        console.log('✏️ Starting edit for note ID:', id);
        console.log('Original location:', lat, lng);

        editingNote = { id, lat, lng };
        originalLat = lat;
        originalLng = lng;
        originalPrivacy = privacy;

        document.getElementById('noteModal').querySelector('.modal-header').textContent = 'Edit Note';
        document.getElementById('noteText').value = text;

        const textarea = document.getElementById('noteText');
        textarea.value = text;

        setupDynamicTextarea(textarea);
        
        document.querySelectorAll('input[name="privacy"]').forEach(radio => {
            radio.checked = (radio.value === privacy);
        });

        const modalButtons = document.querySelector('.modal-buttons');
        if (!document.getElementById('changeLocationBtn')) {
            const changeLocationBtn = document.createElement('button');
            changeLocationBtn.id = 'changeLocationBtn';
            changeLocationBtn.textContent = '📍 Change Location';
            changeLocationBtn.style.background = '#FF9800';
            changeLocationBtn.style.color = 'white';
            changeLocationBtn.style.marginRight = 'auto';
            changeLocationBtn.style.border = 'none';
            changeLocationBtn.style.padding = '10px 18px';
            changeLocationBtn.style.borderRadius = '4px';
            changeLocationBtn.style.cursor = 'pointer';
            
            changeLocationBtn.onclick = startLocationEdit;
            
            modalButtons.insertBefore(changeLocationBtn, modalButtons.firstChild);
        }

        document.getElementById('noteModal').showModal();
    }

    function startNewNoteLocationEdit() {
        if (editingNote) {
            // If we're editing an existing note, use the existing function
            startLocationEdit();
            return;
        }
        
        // For new notes, we don't have a note ID yet
        // Store that we're editing location for a new note
        isEditingLocation = true;
        isNewNoteLocationEdit = true;
        
        // Close the modal
        document.getElementById('noteModal').close();
        
        // Change cursor to crosshair
        map.getCanvas().style.cursor = 'crosshair';
        
        // Show instruction
        alert('Click anywhere on the map to set the location for this new note');
        
        // Set up one-time click handler for new location
        map.once('click', handleNewNoteLocationSelect);
    }

    function handleNewNoteLocationSelect(e) {
        if (!isEditingLocation || !isNewNoteLocationEdit) return;
        
        // Update the stored click location
        clickLat = e.lngLat.lat;
        clickLng = e.lngLat.lng;
        
        // Show a temporary marker at the new location
        if (tempMarker) {
            tempMarker.remove();
        }
        
        // Create temporary marker at new location
        const tempMarkerElement = document.createElement('div');
        tempMarkerElement.style.width = '24px';
        tempMarkerElement.style.height = '24px';
        tempMarkerElement.style.background = '#4CAF50'; // Green for new note
        tempMarkerElement.style.border = '3px solid white';
        tempMarkerElement.style.borderRadius = '50%';
        tempMarkerElement.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
        tempMarkerElement.style.opacity = '0.8';
        
        tempMarker = new mapboxgl.Marker({ element: tempMarkerElement })
            .setLngLat([clickLng, clickLat])
            .addTo(map);
        
        // Ask for confirmation
        if (confirm('Use this location for your new note?')) {
            // Clean up temp marker
            if (tempMarker) {
                tempMarker.remove();
                tempMarker = null;
            }
            
            // Reset cursor
            map.getCanvas().style.cursor = '';
            
            // Reopen the modal
            document.getElementById('noteModal').showModal();
            
            // Reset editing state
            isEditingLocation = false;
            isNewNoteLocationEdit = false;
        } else {
            // Let them try again
            map.once('click', handleNewNoteLocationSelect);
        }
    }

    function startLocationEdit() {
        if (!editingNote) return;
        
        document.getElementById('noteModal').close();
        
        isEditingLocation = true;
        
        originalMarker = markers.find(m => m.noteId === editingNote.id);
        
        if (originalMarker) {
            const grayMarker = document.createElement('div');
            grayMarker.style.width = '24px';
            grayMarker.style.height = '24px';
            grayMarker.style.background = '#9e9e9e';
            grayMarker.style.border = '3px solid white';
            grayMarker.style.borderRadius = '50%';
            grayMarker.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
            grayMarker.style.opacity = '0.7';
            
            tempMarker = new mapboxgl.Marker({ element: grayMarker })
                .setLngLat([editingNote.lng, editingNote.lat])
                .addTo(map);
            
            originalMarker.remove();
        }
        
        alert('Click anywhere on the map to set the new location for this note');
        
        map.getCanvas().style.cursor = 'crosshair';
        
        map.once('click', handleNewLocation);
    }

    function handleNewLocation(e) {
        if (!isEditingLocation) return;
        
        if (tempMarker) {
            tempMarker.setLngLat([e.lngLat.lng, e.lngLat.lat]);
        }
        
        editingNote.lat = e.lngLat.lat;
        editingNote.lng = e.lngLat.lng;
        
        if (confirm('Use this new location for your note?')) {
            finishLocationEdit(true);
        } else {
            editingNote.lat = originalLat;
            editingNote.lng = originalLng;
            if (tempMarker) {
                tempMarker.setLngLat([originalLng, originalLat]);
            }
            map.once('click', handleNewLocation);
        }
    }

    function finishLocationEdit(confirmed) {
        if (confirmed) {
            if (tempMarker) {
                tempMarker.remove();
                tempMarker = null;
            }
            document.getElementById('noteModal').showModal();
        } else {
            cancelLocationEdit();
        }
        
        map.getCanvas().style.cursor = '';
        isEditingLocation = false;
    }

    function cancelLocationEdit() {
        if (tempMarker) {
            tempMarker.remove();
            tempMarker = null;
        }
        
        if (originalMarker) {
            originalMarker.addTo(map);
        }
        
        editingNote.lat = originalLat;
        editingNote.lng = originalLng;
        
        document.getElementById('noteModal').showModal();
        
        map.getCanvas().style.cursor = '';
        isEditingLocation = false;
    }


    // Edit button event delegation
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('edit-note-btn')) {
            const btn = e.target;
            startEdit(
                parseInt(btn.dataset.id),
                parseFloat(btn.dataset.lat),
                parseFloat(btn.dataset.lng),
                btn.dataset.text,
                btn.dataset.privacy
            );
        }
    });

    // Cancel modal
    document.getElementById('cancelNote').onclick = () => {
        document.getElementById('noteModal').close();
        document.getElementById('noteModal').querySelector('.modal-header').textContent = 'Add New Note';
        
        if (isEditingLocation) {
            cancelLocationEdit();
        }
        
        const changeLocationBtn = document.getElementById('changeLocationBtn');
        if (changeLocationBtn) changeLocationBtn.remove();
        
        editingNote = null;
    };

})(window);
</script>
    </body>
    </html>
    '''
    return render_template_string(html, current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials', 'error')

    html = '''
    <!DOCTYPE html>
    <html><head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#f0f4f8">
    <title>Login</title></head><body>
        <style>
        @media (max-width: 480px) {
        .auth-card {
            width: 100vw;
            min-height: auto;
            margin: 0;
            border-radius: 0;
            padding: 40px 20px;
            box-shadow: none;
        }
    }

        .auth-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .auth-card {
            background: white;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.35);
            width: 100%;
            max-width: 420px;          /* slightly wider */
            padding: 40px 24px;
            animation: slideUp 0.6s ease-out;
        }

        @media (max-width: 480px) {
            .auth-card {
                padding: 32px 20px;
                border-radius: 20px;
                max-width: 100%;       /* full width on small screens */
                margin: 0 16px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }
        }

        .auth-header {
            text-align: center;
            margin-bottom: 32px;
        }

        .auth-header h1 {
            font-size: clamp(1.8rem, 8vw, 2.4rem);
            color: #1a1a1a;
            margin-bottom: 8px;
            font-weight: 700;
        }

        .auth-header p {
            color: #555;
            font-size: 1rem;
        }

        .auth-form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .input-group {
            position: relative;
        }

        .input-group input {
            width: 100%;
            padding: 16px 16px 16px 48px;
            border: 2px solid #d0d0d0;
            border-radius: 16px;
            font-size: 1.05rem;
            transition: all 0.25s ease;
            box-sizing: border-box;
            background: #fafafa;
        }

        .input-group input:focus {
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.18);
            outline: none;
        }

        .input-group .icon {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.4rem;
            color: #888;
        }

        .auth-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 16px;
            border-radius: 16px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
            margin-top: 8px;
            min-height: 54px;          /* better touch target */
        }

        .auth-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 24px rgba(102, 126, 234, 0.35);
        }

        .auth-button:active {
            transform: translateY(0);
        }

        .auth-footer {
            text-align: center;
            margin-top: 28px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 0.95rem;
        }

        .auth-footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }

        .auth-footer a:hover {
            color: #5a6fd9;
            text-decoration: underline;
        }

        /* Flash messages */
        .flash-message,
        .flash-success {
            padding: 14px;
            border-radius: 12px;
            margin-bottom: 24px;
            text-align: center;
            font-size: 0.95rem;
        }

        .flash-message {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ef9a9a;
        }

        .flash-success {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #a5d6a7;
        }

        /* Ensure good spacing on very small screens */
        @media (max-width: 360px) {
            .auth-card {
                padding: 24px 16px;
            }
            .auth-button {
                font-size: 1rem;
            }
        }
        </style>

<div class="auth-container">
    <div class="auth-card">
        <div class="auth-header">
            <h1>📍 LeelaMaps</h1>
            <p>Welcome back! Please sign in to continue</p>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message {% if category == 'success' %}flash-success{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" class="auth-form">
            <div class="input-group">
                <span class="icon">👤</span>
                <input type="text" name="username" placeholder="Username" required autocomplete="username">
            </div>
            
            <div class="input-group">
                <span class="icon">🔒</span>
                <input type="password" name="password" placeholder="Password" required autocomplete="current-password">
            </div>
            
            <button type="submit" class="auth-button">Sign In</button>
        </form>
        
        <div class="auth-footer">
            Don't have an account? <a href="{{ url_for('register') }}">Create one</a>
        </div>
    </div>
</div>
    </body></html>
    '''
    return render_template_string(html)

from sqlalchemy import or_, and_, func

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    is_location = request.args.get('location', 'false').lower() == 'true'
    
    if not query or len(query) < 3:
        return jsonify([])
    
    results = []
    
    # 1. SEARCH BY LOCATION (using Mapbox Geocoding API)
    if is_location:
        try:
            # Call Mapbox Geocoding API
            import requests
            mapbox_token = 'YOUR_MAPBOX_TOKEN'  # Use the same token
            geocode_url = f"https://api.mapbox.com/search/geocode/v6/forward?q={requests.utils.quote(query)}&access_token={mapbox_token}&limit=5"
            
            response = requests.get(geocode_url)
            if response.status_code == 200:
                data = response.json()
                for feature in data.get('features', []):
                    results.append({
                        'id': f"loc_{len(results)}",
                        'type': 'location',
                        'title': feature['properties']['name'],
                        'subtitle': feature['properties'].get('place_formatted', ''),
                        'lat': feature['geometry']['coordinates'][1],
                        'lng': feature['geometry']['coordinates'][0]
                    })
        except Exception as e:
            app.logger.error(f"Geocoding error: {e}")
    
    # 2. SEARCH BY NOTE TEXT AND AUTHOR
    # Get notes visible to current user
    public_notes = Note.query.filter_by(privacy='public')
    own_private_notes = Note.query.filter_by(user_id=current_user.id, privacy='private')
    all_visible = public_notes.union(own_private_notes)
    
    # Search in text, address, and author username
    search_pattern = f"%{query}%"
    note_results = all_visible.filter(
        or_(
            Note.text.ilike(search_pattern),
            Note.address.ilike(search_pattern),
            Note.place_name.ilike(search_pattern),
            Note.country.ilike(search_pattern),
            Note.user.has(User.username.ilike(search_pattern))
        )
    ).limit(10).all()
    
    for note in note_results:
        results.append({
            'id': f"note_{note.id}",
            'type': 'note',
            'title': f"📌 {note.user.username}'s note",
            'subtitle': note.text[:100] + ('...' if len(note.text) > 100 else ''),
            'lat': note.lat,
            'lng': note.lng,
            'address': note.address
        })
    
    # 3. If we have location results, prioritize them by relevance
    # Sort results: locations first, then notes
    results.sort(key=lambda x: 0 if x['type'] == 'location' else 1)
    
    return jsonify(results[:10])  # Return top 10 results

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/add_note', methods=['POST'])
@login_required
def add_note():
    try:
        data = request.json
        lat = data.get('lat')
        lng = data.get('lng')
        text = data.get('text')
        privacy = data.get('privacy', 'private')
        user_lat = data.get('user_lat')
        user_lng = data.get('user_lng')

        if lat is None or lng is None or not text:
            return jsonify({'success': False, 'error': 'Missing data'}), 400

        if privacy not in ['public', 'private']:
            privacy = 'private'

        # Reverse geocode to get address
        address = None
        place_name = None
        country = None
        
        try:
            import requests
            mapbox_token = 'YOUR_MAPBOX_TOKEN'
            reverse_url = f"https://api.mapbox.com/search/geocode/v6/reverse?longitude={lng}&latitude={lat}&access_token={mapbox_token}&limit=1"
            
            response = requests.get(reverse_url)
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                if features:
                    props = features[0]['properties']
                    address = props.get('full_address') or props.get('place_formatted')
                    place_name = props.get('place') or props.get('name')
                    # Extract country from context
                    for ctx in features[0].get('properties', {}).get('context', []):
                        if ctx.get('country_code'):
                            country = ctx.get('country')
                            break
        except Exception as e:
            app.logger.error(f"Reverse geocoding error: {e}")

        note = Note(
            lat=lat, lng=lng, text=text,
            privacy=privacy, user_id=current_user.id,
            user_lat=user_lat, user_lng=user_lng,
            address=address,
            place_name=place_name,
            country=country
        )
        
        db.session.add(note)
        db.session.commit()
        return jsonify({'success': True, 'username': current_user.username})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Add note error: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route('/edit_note', methods=['POST'])
@login_required
def edit_note():
    try:
        data = request.json
        note_id = data.get('id')
        lat = data.get('lat')
        lng = data.get('lng')
        text = data.get('text')
        privacy = data.get('privacy', 'private')
        user_lat = data.get('user_lat')
        user_lng = data.get('user_lng')

        if not note_id or lat is None or lng is None or not text:
            return jsonify({'success': False, 'error': 'Missing data'}), 400

        note = Note.query.get(note_id)
        if not note:
            return jsonify({'success': False, 'error': 'Note not found'}), 404

        if note.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        if privacy not in ['public', 'private']:
            privacy = 'private'

        # If location changed, update address
        if note.lat != lat or note.lng != lng:
            try:
                import requests
                mapbox_token = 'YOUR_MAPBOX_TOKEN'
                reverse_url = f"https://api.mapbox.com/search/geocode/v6/reverse?longitude={lng}&latitude={lat}&access_token={mapbox_token}&limit=1"
                
                response = requests.get(reverse_url)
                if response.status_code == 200:
                    data = response.json()
                    features = data.get('features', [])
                    if features:
                        props = features[0]['properties']
                        note.address = props.get('full_address') or props.get('place_formatted')
                        note.place_name = props.get('place') or props.get('name')
                        for ctx in features[0].get('properties', {}).get('context', []):
                            if ctx.get('country_code'):
                                note.country = ctx.get('country')
                                break
            except Exception as e:
                app.logger.error(f"Reverse geocoding error on edit: {e}")

        note.lat = lat
        note.lng = lng
        note.text = text
        note.privacy = privacy
        
        if user_lat is not None and user_lng is not None:
            note.user_lat = user_lat
            note.user_lng = user_lng

        db.session.commit()

        return jsonify({
            'success': True,
            'note': {
                'id': note.id,
                'lat': note.lat,
                'lng': note.lng,
                'text': note.text,
                'privacy': note.privacy,
                'username': current_user.username,
                'created_at': note.created_at.isoformat(),
                'updated_at': note.updated_at.isoformat(),
                'address': note.address or "",
                'is_owner': True
            }
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Edit note error: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route('/get_notes_in_view')
@login_required
def get_notes_in_view():
    """Get notes within specified viewport bounds"""
    bounds = request.args.get('bounds')
    limit = request.args.get('limit', 100, type=int)
    
    if not bounds:
        return jsonify([])  # Return empty array
    
    try:
        sw_lat, sw_lng, ne_lat, ne_lng = map(float, bounds.split(','))
    except:
        return jsonify([])  # Invalid bounds, return empty array
    
    # Get public notes in view
    public_notes = Note.query.filter_by(privacy='public').filter(
        Note.lat.between(sw_lat, ne_lat),
        Note.lng.between(sw_lng, ne_lng)
    )
    
    # Get user's private notes in view
    private_notes = Note.query.filter_by(
        user_id=current_user.id, 
        privacy='private'
    ).filter(
        Note.lat.between(sw_lat, ne_lat),
        Note.lng.between(sw_lng, ne_lng)
    )
    
    # Combine and order
    all_notes = public_notes.union(private_notes).order_by(Note.created_at.desc()).limit(limit).all()
    
    # Format response as array
    result = []
    for n in all_notes:
        username = n.user.username if n.user else "[deleted]"
        result.append({
            'id': n.id,
            'lat': n.lat,
            'lng': n.lng,
            'text': n.text[:200] + ('...' if len(n.text) > 200 else ''),
            'username': username,
            'privacy': n.privacy,
            'created_at': n.created_at.isoformat() if n.created_at else None,
            'updated_at': n.updated_at.isoformat() if n.updated_at else None,
            'is_owner': n.user_id == current_user.id,
            'user_lat': n.user_lat,
            'user_lng': n.user_lng,
            'address': n.address,
            'place_name': n.place_name,
            'country': n.country
        })
    
    return jsonify(result)


@app.route('/get_notes')
@login_required
def get_notes():
    # Get viewport bounds from request
    bounds = request.args.get('bounds')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    search_query = request.args.get('q', '')
    prioritize_direction = request.args.get('direction')  # e.g., "north", "south"
    
    # Base query for visible notes
    public_notes = Note.query.filter_by(privacy='public')
    own_private_notes = Note.query.filter_by(user_id=current_user.id, privacy='private')
    
    # Combine queries properly
    all_visible = public_notes.union(own_private_notes)
    
    # Apply viewport filtering if bounds provided
    if bounds:
        try:
            # bounds format: "sw_lat,sw_lng,ne_lat,ne_lng"
            sw_lat, sw_lng, ne_lat, ne_lng = map(float, bounds.split(','))
            
            # Create a subquery with filters before applying union
            public_filtered = Note.query.filter_by(privacy='public').filter(
                Note.lat.between(sw_lat, ne_lat),
                Note.lng.between(sw_lng, ne_lng)
            )
            private_filtered = Note.query.filter_by(
                user_id=current_user.id, 
                privacy='private'
            ).filter(
                Note.lat.between(sw_lat, ne_lat),
                Note.lng.between(sw_lng, ne_lng)
            )
            
            all_visible = public_filtered.union(private_filtered)
        except Exception as e:
            app.logger.error(f"Bounds parsing error: {e}")
            # If bounds invalid, continue without filtering
            pass
    
    # Apply search filtering if query provided
    if search_query:
        search_pattern = f"%{search_query}%"
        # Need to recreate the filtered query with search
        public_filtered = Note.query.filter_by(privacy='public').filter(
            db.or_(
                Note.text.ilike(search_pattern),
                Note.address.ilike(search_pattern),
                Note.user.has(User.username.ilike(search_pattern))
            )
        )
        private_filtered = Note.query.filter_by(
            user_id=current_user.id, 
            privacy='private'
        ).filter(
            db.or_(
                Note.text.ilike(search_pattern),
                Note.address.ilike(search_pattern),
                Note.user.has(User.username.ilike(search_pattern))
            )
        )
        all_visible = public_filtered.union(private_filtered)
    
    # Get total count BEFORE pagination
    total_count = all_visible.count()
    
    # Order by recency
    all_visible = all_visible.order_by(Note.created_at.desc())
    
    # Apply pagination AFTER ordering
    paginated = all_visible.offset(offset).limit(limit).all()
    
    # Format response
    result = []
    for n in paginated:
        # Safely get username
        username = "[deleted]"
        if n.user:
            username = n.user.username
        
        result.append({
            'id': n.id,
            'lat': n.lat,
            'lng': n.lng,
            'text': n.text[:200] + ('...' if len(n.text) > 200 else ''),
            'username': username,
            'privacy': n.privacy,
            'created_at': n.created_at.isoformat() if n.created_at else None,
            'updated_at': n.updated_at.isoformat() if n.updated_at else None,
            'is_owner': n.user_id == current_user.id,
            'user_lat': n.user_lat,
            'user_lng': n.user_lng,
            'address': n.address,
            'place_name': n.place_name,
            'country': n.country,
            'has_media': False,
            'media_count': 0
        })
    
    return jsonify({
        'notes': result,
        'total': total_count,
        'has_more': (offset + len(result)) < total_count,
        'bounds': bounds,
        'offset': offset,
        'limit': limit
    })

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password required', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registered! Please log in.', 'success')
        return redirect(url_for('login'))
    
    html = '''
    <!DOCTYPE html>
    <html><head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#f0f4f8">
    <title>Register</title></head><body>
        <style>
        @media (max-width: 480px) {
        .auth-card {
            width: 100vw;
            min-height: auto;
            margin: 0;
            border-radius: 0;
            padding: 40px 20px;
            box-shadow: none;
        }
    }
        .auth-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .auth-card {
            background: white;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.35);
            width: 100%;
            max-width: 420px;          /* slightly wider */
            padding: 40px 24px;
            animation: slideUp 0.6s ease-out;
        }

        @media (max-width: 480px) {
            .auth-card {
                padding: 32px 20px;
                border-radius: 20px;
                max-width: 100%;       /* full width on small screens */
                margin: 0 16px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }
        }

        .auth-header {
            text-align: center;
            margin-bottom: 32px;
        }

        .auth-header h1 {
            font-size: clamp(1.8rem, 8vw, 2.4rem);
            color: #1a1a1a;
            margin-bottom: 8px;
            font-weight: 700;
        }

        .auth-header p {
            color: #555;
            font-size: 1rem;
        }

        .auth-form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .input-group {
            position: relative;
        }

        .input-group input {
            width: 100%;
            padding: 16px 16px 16px 48px;
            border: 2px solid #d0d0d0;
            border-radius: 16px;
            font-size: 1.05rem;
            transition: all 0.25s ease;
            box-sizing: border-box;
            background: #fafafa;
        }

        .input-group input:focus {
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.18);
            outline: none;
        }

        .input-group .icon {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.4rem;
            color: #888;
        }

        .auth-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 16px;
            border-radius: 16px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
            margin-top: 8px;
            min-height: 54px;          /* better touch target */
        }

        .auth-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 24px rgba(102, 126, 234, 0.35);
        }

        .auth-button:active {
            transform: translateY(0);
        }

        .auth-footer {
            text-align: center;
            margin-top: 28px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 0.95rem;
        }

        .auth-footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }

        .auth-footer a:hover {
            color: #5a6fd9;
            text-decoration: underline;
        }

        /* Flash messages */
        .flash-message,
        .flash-success {
            padding: 14px;
            border-radius: 12px;
            margin-bottom: 24px;
            text-align: center;
            font-size: 0.95rem;
        }

        .flash-message {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ef9a9a;
        }

        .flash-success {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #a5d6a7;
        }

        /* Ensure good spacing on very small screens */
        @media (max-width: 360px) {
            .auth-card {
                padding: 24px 16px;
            }
            .auth-button {
                font-size: 1rem;
            }
        }
        </style>

<div class="auth-container">
    <div class="auth-card">
        <div class="auth-header">
            <h1>📍 LeelaMaps</h1>
            <p>Create your account to start mapping!</p>  <!-- optional: friendlier message -->
        </div>
       
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message {% if category == 'success' %}flash-success{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
       
        <form method="POST" class="auth-form">
            <div class="input-group">
                <span class="icon">👤</span>
                <input type="text" name="username" placeholder="Username" required autocomplete="username">
            </div>
           
            <div class="input-group">
                <span class="icon">🔒</span>
                <input type="password" name="password" placeholder="Password" required autocomplete="new-password">
            </div>
           
            <button type="submit" class="auth-button">Register</button>  <!-- ← Changed from "Sign In" to "Register" -->
        </form>
       
        <div class="auth-footer">
            Already have an account? <a href="{{ url_for('login') }}">Sign in</a>
        </div>
    </div>
</div>
    </body></html>
    '''
    return render_template_string(html)

@app.route('/debug-timestamps')
def debug_timestamps():
    notes = Note.query.all()
    return jsonify([
        {
            'id': n.id,
            'created_at': n.created_at.isoformat() if n.created_at else 'MISSING',
            'updated_at': n.updated_at.isoformat() if n.updated_at else 'MISSING'
        } for n in notes
    ])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)