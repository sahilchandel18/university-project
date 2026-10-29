import os
import sys
from pathlib import Path

# Add project root to sys.path so Django apps can be imported
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nodues_project.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
