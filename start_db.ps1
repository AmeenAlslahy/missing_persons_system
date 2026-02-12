# Check if Docker is running
$dockerStatus = docker info
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running or not installed." -ForegroundColor Red
    exit 1
}

# Pull the image
Write-Host "Pulling PostgreSQL image..."
docker pull postgres:15

# Stop and remove existing container if it exists
docker stop missing-db 2>$null
docker rm missing-db 2>$null

# Run the container
Write-Host "Starting PostgreSQL container..."
docker run --name missing-db `
    -e POSTGRES_PASSWORD=postgres `
    -e POSTGRES_USER=postgres `
    -e POSTGRES_DB=missing_persons_db `
    -p 5432:5432 `
    -d postgres:15

# Wait for it to be ready
Write-Host "Waiting for database to be ready..."
Start-Sleep -Seconds 5

Write-Host "✅ Database is ready!"
Write-Host "Host: localhost"
Write-Host "Port: 5432"
Write-Host "User: postgres"
Write-Host "Password: postgres"
Write-Host "DB: missing_persons_db"
