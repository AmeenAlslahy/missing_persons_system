import os
import django
import shutil

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import Report, ReportImage
from matching.models import MatchResult, FaceEmbedding
from django.conf import settings

def clear_data():
    print("Starting data clearance...")
    
    # 1. Delete Match Results
    deleted_matches, _ = MatchResult.objects.all().delete()
    print(f"Deleted {deleted_matches} MatchResults.")
    
    # 2. Delete Face Embeddings
    # Usually cascade delete from ReportImage, but safe to be explicit or if there are orphans
    deleted_embeddings, _ = FaceEmbedding.objects.all().delete()
    print(f"Deleted {deleted_embeddings} FaceEmbeddings.")
    
    # 3. Delete Report Images and Files
    # Deleting the object deletes the file if configured, but let's make sure
    images = ReportImage.objects.all()
    count_images = images.count()
    for img in images:
        if img.image:
            try:
                if os.path.isfile(img.image.path):
                    os.remove(img.image.path)
            except Exception as e:
                print(f"Error removing file {img.image}: {e}")
    
    deleted_images, _ = ReportImage.objects.all().delete()
    print(f"Deleted {deleted_images} ReportImages.")

    # 4. Delete Reports
    # Be careful with Primary Photos
    reports = Report.objects.all()
    for report in reports:
        if report.primary_photo:
             try:
                if os.path.isfile(report.primary_photo.path):
                    os.remove(report.primary_photo.path)
             except Exception as e:
                print(f"Error removing primary photo {report.primary_photo}: {e}")

    deleted_reports, _ = Report.objects.all().delete()
    print(f"Deleted {deleted_reports} Reports.")
    
    # 5. Clean up processed folders if needed (optional)
    # This might be specific to your processed dataset structure
    
    print("Data clearance complete.")

if __name__ == '__main__':
    try:
        clear_data()
    except Exception as e:
        print(f"Error during clearance: {e}")
