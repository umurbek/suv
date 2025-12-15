from django.shortcuts import render, redirect
from django.http import JsonResponse
import csv

# Define a function to read data from the CSV file
def read_csv_data():
    regions = []
    with open('Volidam.csv', 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row if present
        for row in reader:
            if len(row) > 2:  # Ensure there are enough columns
                regions.append({
                    'name': row[0],
                    'bottle': row[1],
                    'location': row[2],
                    'phone': row[3] if len(row) > 3 else ''
                })
    return regions

# View to display regions
def regions_view(request):
    regions = read_csv_data()
    return render(request, 'admin/regions.html', {'regions': regions})

# View to handle region updates
def update_region(request):
    if request.method == 'POST':
        # Logic to update the region in the CSV file
        return JsonResponse({'status': 'success'})

# View to handle region deletion
def delete_region(request):
    if request.method == 'POST':
        # Logic to delete the region from the CSV file
        return JsonResponse({'status': 'success'})

# View to handle adding a new region
def add_region(request):
    if request.method == 'POST':
        # Logic to add a new region to the CSV file
        return JsonResponse({'status': 'success'})