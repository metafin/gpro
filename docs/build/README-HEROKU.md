# G-Code Generator Web Application - Heroku Deployment Instructions

This document provides instructions for Claude Code sessions to deploy the G-code generator web application to Heroku.

## Overview

Deploy the Flask application to Heroku with:
- PostgreSQL database (Heroku Postgres)
- Gunicorn WSGI server
- Automatic SSL
- Environment-based configuration

---

## Prerequisites

Before deployment, ensure you have:
1. Heroku CLI installed
2. Git repository initialized
3. All backend and frontend code complete (see README-SERVER.md and README-UI.md)
4. `requirements.txt` updated with all dependencies

---

## Required Files

### Procfile

Create `Procfile` in the project root (no extension):

```
web: gunicorn app:app
```

### runtime.txt

Create `runtime.txt` in the project root:

```
python-3.13.0
```

### requirements.txt

Ensure `requirements.txt` includes all dependencies:

```
Flask>=3.0.0
gunicorn>=21.0.0
WTForms>=3.1.0
Flask-WTF>=1.2.0
Flask-SQLAlchemy>=3.1.0
Flask-Migrate>=4.0.0
psycopg2-binary>=2.9.0
matplotlib>=3.8.0
numpy>=1.26.0
Pillow>=10.0.0
python-dotenv>=1.0.0
```

### config.py

Ensure `config.py` handles Heroku's DATABASE_URL:

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Database URL - Heroku sets DATABASE_URL automatically
    # For local dev, use SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///gcode.db')

    # Heroku uses postgres:// but SQLAlchemy needs postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

---

## Deployment Steps

### Step 1: Install Heroku CLI

```bash
# macOS (using Homebrew)
brew tap heroku/brew && brew install heroku

# Or download from https://devcenter.heroku.com/articles/heroku-cli
```

### Step 2: Login to Heroku

```bash
heroku login
```

This opens a browser window for authentication.

### Step 3: Create Heroku App

```bash
# Create app with a unique name
heroku create frc-gcode-generator

# Or let Heroku generate a name
heroku create
```

### Step 4: Add PostgreSQL Database

```bash
# Add the Essential-0 tier (free tier was discontinued)
heroku addons:create heroku-postgresql:essential-0

# Verify the addon was created
heroku addons
```

This automatically sets the `DATABASE_URL` environment variable.

### Step 5: Set Environment Variables

```bash
# Generate and set a secure secret key
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Verify config vars
heroku config
```

### Step 6: Initialize Git (if needed)

```bash
# Initialize git repository if not already done
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit - G-Code Generator web app"
```

### Step 7: Deploy to Heroku

```bash
# Add Heroku remote (if not automatically added)
heroku git:remote -a frc-gcode-generator

# Push to Heroku
git push heroku main

# Or if using master branch
git push heroku master
```

### Step 8: Run Database Migrations

```bash
# Run Flask-Migrate upgrade command
heroku run flask db upgrade
```

### Step 9: Seed Default Data

```bash
# Run the seed script
heroku run python seed_data.py
```

### Step 10: Open the Application

```bash
# Open in browser
heroku open

# Or get the URL
heroku info
```

---

## Seed Data Script (seed_data.py)

Create this file in the project root:

```python
from app import create_app, db
from web.models import Material, MachineSettings, GeneralSettings, Tool

app = create_app()

with app.app_context():
    # Add default materials
    if not Material.query.first():
        materials = [
            Material(
                id='aluminum_sheet_0125',
                display_name='Aluminum Sheet 1/8"',
                base_material='aluminum',
                form='sheet',
                thickness=0.125,
                gcode_standards={
                    'drill': {
                        '0.125': {'spindle_speed': 1000, 'feed_rate': 2.0, 'plunge_rate': 1.0, 'pecking_depth': 0.05},
                        '0.1875': {'spindle_speed': 900, 'feed_rate': 1.8, 'plunge_rate': 0.9, 'pecking_depth': 0.04},
                        '0.25': {'spindle_speed': 800, 'feed_rate': 1.5, 'plunge_rate': 0.8, 'pecking_depth': 0.03}
                    },
                    'cut': {
                        '0.125': {'spindle_speed': 10000, 'feed_rate': 10.0, 'plunge_rate': 1.5, 'pass_depth': 0.02},
                        '0.1875': {'spindle_speed': 9000, 'feed_rate': 9.0, 'plunge_rate': 1.2, 'pass_depth': 0.018},
                        '0.25': {'spindle_speed': 8000, 'feed_rate': 8.0, 'plunge_rate': 1.0, 'pass_depth': 0.015}
                    }
                }
            ),
            Material(
                id='aluminum_sheet_025',
                display_name='Aluminum Sheet 1/4"',
                base_material='aluminum',
                form='sheet',
                thickness=0.25,
                gcode_standards={
                    'drill': {
                        '0.125': {'spindle_speed': 800, 'feed_rate': 1.5, 'plunge_rate': 0.8, 'pecking_depth': 0.04},
                        '0.1875': {'spindle_speed': 750, 'feed_rate': 1.3, 'plunge_rate': 0.7, 'pecking_depth': 0.035},
                        '0.25': {'spindle_speed': 700, 'feed_rate': 1.2, 'plunge_rate': 0.6, 'pecking_depth': 0.03}
                    },
                    'cut': {
                        '0.125': {'spindle_speed': 8000, 'feed_rate': 8.0, 'plunge_rate': 1.0, 'pass_depth': 0.015},
                        '0.1875': {'spindle_speed': 7500, 'feed_rate': 7.0, 'plunge_rate': 0.9, 'pass_depth': 0.012},
                        '0.25': {'spindle_speed': 7000, 'feed_rate': 6.0, 'plunge_rate': 0.8, 'pass_depth': 0.01}
                    }
                }
            ),
            Material(
                id='polycarbonate_sheet_025',
                display_name='Polycarbonate Sheet 1/4"',
                base_material='polycarbonate',
                form='sheet',
                thickness=0.25,
                gcode_standards={
                    'drill': {
                        '0.125': {'spindle_speed': 2000, 'feed_rate': 4.0, 'plunge_rate': 2.0, 'pecking_depth': 0.1},
                        '0.1875': {'spindle_speed': 1800, 'feed_rate': 3.5, 'plunge_rate': 1.8, 'pecking_depth': 0.08},
                        '0.25': {'spindle_speed': 1600, 'feed_rate': 3.0, 'plunge_rate': 1.5, 'pecking_depth': 0.07}
                    },
                    'cut': {
                        '0.125': {'spindle_speed': 15000, 'feed_rate': 20.0, 'plunge_rate': 3.0, 'pass_depth': 0.05},
                        '0.1875': {'spindle_speed': 14000, 'feed_rate': 18.0, 'plunge_rate': 2.5, 'pass_depth': 0.04},
                        '0.25': {'spindle_speed': 13000, 'feed_rate': 16.0, 'plunge_rate': 2.0, 'pass_depth': 0.035}
                    }
                }
            ),
            Material(
                id='aluminum_tube_2x1_0125',
                display_name='Aluminum Tube 2x1 (0.125" wall)',
                base_material='aluminum',
                form='tube',
                outer_width=2.0,
                outer_height=1.0,
                wall_thickness=0.125,
                gcode_standards={
                    'drill': {
                        '0.125': {'spindle_speed': 1000, 'feed_rate': 2.0, 'plunge_rate': 1.0, 'pecking_depth': 0.05},
                        '0.1875': {'spindle_speed': 900, 'feed_rate': 1.8, 'plunge_rate': 0.9, 'pecking_depth': 0.04}
                    },
                    'cut': {
                        '0.125': {'spindle_speed': 10000, 'feed_rate': 10.0, 'plunge_rate': 1.5, 'pass_depth': 0.02},
                        '0.1875': {'spindle_speed': 9000, 'feed_rate': 9.0, 'plunge_rate': 1.2, 'pass_depth': 0.018}
                    }
                }
            ),
            Material(
                id='aluminum_tube_1x1_0063',
                display_name='Aluminum Tube 1x1 (0.063" wall)',
                base_material='aluminum',
                form='tube',
                outer_width=1.0,
                outer_height=1.0,
                wall_thickness=0.063,
                gcode_standards={
                    'drill': {
                        '0.125': {'spindle_speed': 1200, 'feed_rate': 2.5, 'plunge_rate': 1.2, 'pecking_depth': 0.03}
                    },
                    'cut': {
                        '0.125': {'spindle_speed': 12000, 'feed_rate': 12.0, 'plunge_rate': 2.0, 'pass_depth': 0.015}
                    }
                }
            ),
        ]
        db.session.add_all(materials)
        print(f"Added {len(materials)} materials")

    # Add default machine settings
    if not MachineSettings.query.first():
        machine = MachineSettings(
            name='OMIO CNC',
            max_x=15.0,
            max_y=15.0,
            units='inches',
            controller_type='mach3',
            supports_loops=True,
            supports_canned_cycles=True
        )
        db.session.add(machine)
        print("Added machine settings")

    # Add default general settings
    if not GeneralSettings.query.first():
        general = GeneralSettings(
            safety_height=0.5,
            travel_height=0.2,
            spindle_warmup_seconds=2
        )
        db.session.add(general)
        print("Added general settings")

    # Add default tools
    if not Tool.query.first():
        tools = [
            Tool(tool_type='drill', size=0.125, description='1/8" drill bit'),
            Tool(tool_type='drill', size=0.1875, description='3/16" drill bit'),
            Tool(tool_type='drill', size=0.25, description='1/4" drill bit'),
            Tool(tool_type='drill', size=0.3125, description='5/16" drill bit'),
            Tool(tool_type='end_mill', size=0.125, description='1/8" end mill'),
            Tool(tool_type='end_mill', size=0.1875, description='3/16" end mill'),
            Tool(tool_type='end_mill', size=0.25, description='1/4" end mill'),
        ]
        db.session.add_all(tools)
        print(f"Added {len(tools)} tools")

    db.session.commit()
    print("Seed data added successfully!")
```

---

## Database Management

### Creating Migrations (Local Development)

```bash
# Initialize migrations (first time only)
flask db init

# After model changes, create migration
flask db migrate -m "Description of changes"

# Apply migration locally
flask db upgrade
```

### Applying Migrations on Heroku

```bash
# After deploying code with new migrations
heroku run flask db upgrade
```

### Viewing Database

```bash
# Connect to Heroku Postgres
heroku pg:psql

# Run SQL queries
\dt                      # List tables
SELECT * FROM project;   # Query projects
\q                       # Exit
```

### Database Backup

```bash
# Create a backup
heroku pg:backups:capture

# Download backup
heroku pg:backups:download
```

---

## Monitoring and Debugging

### View Logs

```bash
# Stream logs in real-time
heroku logs --tail

# View recent logs
heroku logs -n 200

# Filter by dyno type
heroku logs --dyno web
```

### Check Application Status

```bash
# View dyno status
heroku ps

# View app info
heroku info

# Check config vars
heroku config
```

### Restart Application

```bash
# Restart all dynos
heroku restart

# Restart specific dyno
heroku restart web.1
```

### Run One-off Commands

```bash
# Open Python shell
heroku run python

# Run Flask shell
heroku run flask shell

# Run any command
heroku run bash
```

---

## Scaling

### Scale Dynos

```bash
# Scale to 1 web dyno (default)
heroku ps:scale web=1

# Scale to 0 (pause app)
heroku ps:scale web=0

# Scale up (requires paid plan)
heroku ps:scale web=2
```

### Upgrade Dyno Type

```bash
# View available dyno types
heroku ps:type

# Upgrade to Basic
heroku ps:type web=basic
```

---

## Troubleshooting

### Common Issues

**1. Application Error (H10)**
```bash
# Check logs for details
heroku logs --tail

# Common causes:
# - Missing Procfile
# - Import errors
# - Missing dependencies in requirements.txt
```

**2. Database Connection Error**
```bash
# Verify DATABASE_URL is set
heroku config:get DATABASE_URL

# Check if postgres addon is attached
heroku addons
```

**3. Static Files Not Loading**
```bash
# Flask serves static files automatically in debug mode
# For production, consider using WhiteNoise or a CDN
pip install whitenoise

# Add to app.py:
from whitenoise import WhiteNoise
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')
```

**4. Migration Errors**
```bash
# Reset migrations (caution: data loss)
heroku pg:reset DATABASE_URL --confirm app-name
heroku run flask db upgrade
heroku run python seed_data.py
```

### Debug Mode on Heroku

Never run Flask in debug mode on Heroku. Debug mode is controlled by environment:

```python
# In app.py - Gunicorn handles this
if __name__ == '__main__':
    app.run(debug=True)  # Only for local development
```

---

## Continuous Deployment

### GitHub Integration

1. Go to Heroku Dashboard > Your App > Deploy
2. Connect to GitHub
3. Select repository
4. Enable automatic deploys from `main` branch

### Manual Deploy from GitHub

```bash
# Deploy specific branch
git push heroku feature-branch:main
```

---

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key for sessions | Yes |
| `DATABASE_URL` | PostgreSQL connection URL | Auto-set by Heroku |
| `FLASK_ENV` | Environment (production/development) | No |

---

## Local Development vs Production

### Local Development

```bash
# Use SQLite
export DATABASE_URL=sqlite:///gcode.db

# Run with debug
flask run --debug
```

### Production (Heroku)

- Uses PostgreSQL (DATABASE_URL set automatically)
- Uses Gunicorn (specified in Procfile)
- Debug mode disabled
- HTTPS enforced

---

## Post-Deployment Verification

### Testing Checklist

1. **Home Page**
   ```bash
   heroku open
   ```
   - Verify page loads
   - Check navigation works

2. **Settings Management**
   - Navigate to `/settings`
   - Verify default materials are present
   - Try adding a new material
   - Check machine settings

3. **Project Creation**
   - Create a new drill project
   - Add operations
   - Save and verify persistence
   - Refresh page - data should persist

4. **G-Code Generation**
   - Open saved project
   - Click "Download G-Code"
   - Verify file downloads
   - Check G-code content

5. **Preview**
   - Open project editor
   - Add operations
   - Click "Refresh Preview"
   - Verify SVG renders

6. **Database Persistence**
   - Create project
   - Restart app: `heroku restart`
   - Verify project still exists

### Performance Check

```bash
# Check response time
curl -w "@curl-format.txt" -o /dev/null -s https://your-app.herokuapp.com/

# Monitor memory usage
heroku logs --tail | grep memory
```

---

## Cost Considerations

### Heroku Pricing (as of 2024)

| Resource | Tier | Cost |
|----------|------|------|
| Dyno | Eco | $5/month |
| Dyno | Basic | $7/month |
| Postgres | Essential-0 | $5/month |
| Postgres | Essential-1 | $9/month |

**Minimum production cost**: ~$10-12/month

### Cost Optimization

1. Use Eco dynos for low-traffic apps
2. Scale to 0 dynos when not in use
3. Use Essential-0 Postgres for small databases
4. Consider Railway or Render as alternatives

---

## Alternative Deployment Options

If Heroku doesn't fit your needs:

### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Render
1. Connect GitHub repository
2. Select Python environment
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`

### DigitalOcean App Platform
1. Connect GitHub repository
2. Configure as Python app
3. Add PostgreSQL database
4. Deploy

---

## Quick Reference Commands

```bash
# Deploy
git push heroku main

# View logs
heroku logs --tail

# Run migrations
heroku run flask db upgrade

# Seed data
heroku run python seed_data.py

# Restart
heroku restart

# Open app
heroku open

# Database console
heroku pg:psql

# Scale dynos
heroku ps:scale web=1

# View config
heroku config

# Set config
heroku config:set KEY=value
```
