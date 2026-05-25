# Fair Admin Dashboard

This is the backend API and administrative dashboard for the **Fair** platform, built with Django, Django REST Framework, and PostgreSQL. It is designed to be managed exclusively by the Angeles City LGU and PTRO (Public Transport Regulatory Office).

> **Note:** For complete, platform-wide setup instructions (including the mobile commuter app), please see the Master `README.md` located in the root of the `fair` repository.

## 🛠️ Quick Backend Setup

1. **Prerequisites:** Python 3.10+ and PostgreSQL installed locally.
2. **Virtual Environment:** 
   ```bash
   python -m venv venv
   
   # Activate (Windows)
   venv\Scripts\activate  
   
   # Activate (macOS/Linux)
   source venv/bin/activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables:** Create a `.env` file in this directory based on your local Postgres setup.
   ```env
   SECRET_KEY=your_django_secret_key
   DEBUG=True
   DB_NAME=fair_db
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_HOST=localhost
   DB_PORT=5432
   ```
5. **Migrate & Run:**
   ```bash
   # Initialize database schema
   python manage.py migrate
   
   # Create PTRO admin account
   python manage.py createsuperuser  
   
   # Start the development server
   python manage.py runserver
   ```
