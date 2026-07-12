$clean_path = "C:\Users\Mauro\Documents\nq-backtest-clean-clean"

Get-ChildItem -Path $clean_path -Recurse -File | ForEach-Object {
    $ext = $_.Extension.ToLower()
    # Only process text files, exclude binary/large files
    if ($ext -in (".py", ".json", ".ps1", ".txt", ".md", ".env", ".example", ".js", ".jsx", ".css", ".html")) {
        $raw_content = Get-Content $_.FullName -Raw
        if ($raw_content -match "nq-backtest-clean") {
            # Replace case-insensitive references
            $new_content = $raw_content -replace "nq-backtest-clean", "nq-backtest-clean-clean"
            Set-Content $_.FullName -Value $new_content
            Write-Host "Updated: $($_.FullName)" -ForegroundColor Green
        }
    }
}

