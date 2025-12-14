# File Upload


Send already existing


Create and send
```bash
curl -X POST http://localhost:8088/api/files/upload \
  -H "Accept: application/json" \
  -F "file=@./test_files/sample.pdf" \
  -F "filename=sample.pdf" \
  -F "description=Test upload for demo"
```


# FIle Upload without optional description field

```bash
echo "This is a demo file uploaded via curl" > /tmp/demo.txt && \
curl -v -X POST http://localhost:8088/api/files/upload \
  -H "Accept: application/json" \
  -F "file=@/tmp/demo.txt" \
  -F "filename=demo.txt" \
  -F "description=Created and uploaded in one command" | jq && \
rm /tmp/demo.txt
```


# File too large error
```bash
dd if=/dev/zero of=/tmp/big.bin bs=1M count=51 && \
curl -v http://localhost:8088/api/files/upload \
  -H "Accept: application/json" \
  -F "file=@/tmp/big.bin" \
  -F "filename=big.bin" \
  -F "description=51MB file should fail" | jq && \
rm /tmp/big.bin
```