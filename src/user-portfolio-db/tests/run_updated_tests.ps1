# PowerShell test runner script for User Portfolio Database

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "User Portfolio Database Updated Tests" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Function to print colored output
function Write-TestResult {
    param(
        [bool]$Success,
        [string]$Message
    )
    
    if ($Success) {
        Write-Host "✓ $Message" -ForegroundColor Green
    } else {
        Write-Host "✗ $Message" -ForegroundColor Red
    }
}

# Check if PostgreSQL client is available
try {
    $psqlVersion = & psql --version 2>$null
    Write-Host "PostgreSQL client found: $psqlVersion" -ForegroundColor Green
} catch {
    Write-Host "PostgreSQL client (psql) is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install PostgreSQL client tools" -ForegroundColor Yellow
    exit 1
}

# Try to connect to a database
Write-Host "`nChecking database connection..." -ForegroundColor Blue

$connectionSuccess = $false
$testDbName = "test_user_portfolio_db"

# Try different connection methods
if ($env:DATABASE_URL) {
    Write-Host "Using DATABASE_URL for connection" -ForegroundColor Yellow
    try {
        & psql $env:DATABASE_URL -c "SELECT 1;" 2>$null
        $connectionSuccess = $true
        Write-Host "Database connection successful using DATABASE_URL" -ForegroundColor Green
    } catch {
        Write-Host "Cannot connect to database using DATABASE_URL" -ForegroundColor Red
    }
} else {
    # Try local connection
    Write-Host "Trying local connection (localhost:5432)" -ForegroundColor Yellow
    try {
        & psql -h localhost -p 5432 -U postgres -d postgres -c "SELECT 1;" 2>$null
        $connectionSuccess = $true
        Write-Host "Database connection successful using local connection" -ForegroundColor Green
    } catch {
        Write-Host "Cannot connect to local database" -ForegroundColor Red
        Write-Host "Please ensure PostgreSQL is running and accessible" -ForegroundColor Yellow
        Write-Host "Or set DATABASE_URL environment variable" -ForegroundColor Yellow
        exit 1
    }
}

if (-not $connectionSuccess) {
    Write-Host "No working database connection found" -ForegroundColor Red
    exit 1
}

# Create test database
Write-Host "`nSetting up test database..." -ForegroundColor Blue

try {
    if ($env:DATABASE_URL) {
        # Create test database using DATABASE_URL
        & psql $env:DATABASE_URL -c "DROP DATABASE IF EXISTS $testDbName;" 2>$null
        & psql $env:DATABASE_URL -c "CREATE DATABASE $testDbName;" 2>$null
        $testDatabaseUrl = $env:DATABASE_URL -replace "/[^/]+$", "/$testDbName"
    } else {
        # Create test database using local connection
        & psql -h localhost -p 5432 -U postgres -d postgres -c "DROP DATABASE IF EXISTS $testDbName;" 2>$null
        & psql -h localhost -p 5432 -U postgres -d postgres -c "CREATE DATABASE $testDbName;" 2>$null
    }
    Write-Host "Test database created successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to create test database" -ForegroundColor Red
    exit 1
}

# Load schema into test database
Write-Host "`nLoading database schema..." -ForegroundColor Blue

try {
    if ($env:DATABASE_URL) {
        & psql $testDatabaseUrl -f "../initdb/0-user-portfolio-schema.sql" 2>$null
    } else {
        & psql -h localhost -p 5432 -U postgres -d $testDbName -f "../initdb/0-user-portfolio-schema.sql" 2>$null
    }
    Write-Host "Schema loaded successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to load schema" -ForegroundColor Red
    exit 1
}

# Run the updated test
Write-Host "`nStarting test execution..." -ForegroundColor Yellow

$testPassed = $true

try {
    if ($env:DATABASE_URL) {
        & psql $testDatabaseUrl -f "test_user_portfolio_db_updated.sql" 2>$null
    } else {
        & psql -h localhost -p 5432 -U postgres -d $testDbName -f "test_user_portfolio_db_updated.sql" 2>$null
    }
    
    if ($LASTEXITCODE -eq 0) {
        $testPassed = $true
    } else {
        $testPassed = $false
    }
} catch {
    $testPassed = $false
}

# Summary
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-TestResult $testPassed "Comprehensive Database Tests"

Write-Host "`nTotal Tests: 1"
Write-Host "Passed: $(if ($testPassed) { '1' } else { '0' })"
Write-Host "Failed: $(if ($testPassed) { '0' } else { '1' })"

if ($testPassed) {
    Write-Host "`nAll tests passed! 🎉" -ForegroundColor Green
    Write-Host "User Portfolio Database is working correctly!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome tests failed. Please check the output above." -ForegroundColor Red
    exit 1
}
