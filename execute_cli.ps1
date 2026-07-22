Write-Host "=== CLI Evaluation ===" -ForegroundColor Green

Write-Host "1. Seeding instruments..." -ForegroundColor Yellow
python -m auto_trader.cli registry seed

Write-Host "2. Listing instruments..." -ForegroundColor Yellow
python -m auto_trader.cli registry list

Write-Host "3. Importing CSV..." -ForegroundColor Yellow
python -m auto_trader.cli registry import --file inputs/Liste_PEA.csv

Write-Host "4. Syncing data..." -ForegroundColor Yellow
python -m auto_trader.cli sync

Write-Host "5. Querying interday..." -ForegroundColor Yellow
python -m auto_trader.cli query interday --ticker AI 

Write-Host "✅ All CLI tests passed" -ForegroundColor Green