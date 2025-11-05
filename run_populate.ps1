# PowerShell script to run populate_sample_data.py
Write-Host "🚀 Running populate_sample_data.py..." -ForegroundColor Green
Get-Content populate_sample_data.py | python manage.py shell
Write-Host "✅ Done!" -ForegroundColor Green
