# Get sales data
```bash
curl -s http://localhost:8080/api/sales \
  -H "Accept: application/json" | jq
```

# Download sales pdf
```bash
curl -s http://localhost:8080/api/sales/export \
  -H "Accept: application/pdf" \
  --output sales-report.pdf
```