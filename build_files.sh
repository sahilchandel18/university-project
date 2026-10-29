#!/bin/bash
# Vercel custom build script
echo "Building project for Vercel deployment..."
python3 -m pip install -r requirements.txt
python3 manage.py collectstatic --noinput --clear
echo "Build completed successfully."
