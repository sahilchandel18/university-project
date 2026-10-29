"""
Production WSGI Server Runner for University No Dues System.
Powered by Waitress (Production-grade, pure-Python WSGI server for Windows & Linux).
"""
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nodues_project.settings')
    try:
        from waitress import serve
        from nodues_project.wsgi import application
    except ImportError as e:
        print(f"Error importing server dependencies: {e}")
        sys.exit(1)

    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8000))
    
    print("=" * 65)
    print("  UNIVERSITY NO DUES VERIFICATION SYSTEM - PRODUCTION SERVER")
    print("=" * 65)
    print(f" * Serving WSGI application with Waitress (Production Mode)")
    print(f" * Local URL:   http://127.0.0.1:{port}/")
    print(f" * Network URL: http://localhost:{port}/")
    print(f" * Press Ctrl+C to stop the server.")
    print("=" * 65)
    
    serve(application, host=host, port=port, threads=6)

if __name__ == '__main__':
    main()
