# Health Monitoring - Testing Guide

## Overview
This example demonstrates:
- REST CRUD: Patient profiles, health goals, medications
- **Per-operation RBAC**: Medications (patients can read/create, only doctors can update/delete)
- WebSocket inbound: Real-time heart rate from wearables
- WebSocket outbound: Emergency SOS alerts
- Composite entities: Health summary with BMI calculation

## Base URL
```
http://localhost:8080
```

---

## Step 1: Generate JWT Tokens

Run this command to generate test tokens (valid for 1 hour):

```bash
python -c "
import jwt
import time

SECRET = 'GAqdSt3UtW6EWI5IC6njVdon4OOmgjWS'  # From .env HEALTH_JWT_SECRET

# Patient token
patient = jwt.encode({
    'sub': 'patient123',
    'roles': ['patient'],
    'exp': int(time.time()) + 3600
}, SECRET, algorithm='HS256')
print('PATIENT_TOKEN=' + patient)

# Doctor token
doctor = jwt.encode({
    'sub': 'doctor456',
    'roles': ['doctor'],
    'exp': int(time.time()) + 3600
}, SECRET, algorithm='HS256')
print('DOCTOR_TOKEN=' + doctor)

# Invalid role token (for testing rejection)
admin = jwt.encode({
    'sub': 'admin789',
    'roles': ['admin'],
    'exp': int(time.time()) + 3600
}, SECRET, algorithm='HS256')
print('ADMIN_TOKEN=' + admin)
"
```

**Set the tokens as environment variables:**
```bash
export PATIENT_TOKEN="<paste patient token here>"
export DOCTOR_TOKEN="<paste doctor token here>"
export ADMIN_TOKEN="<paste admin token here>"
```

---

## Step 2: Test Authentication

### 2.1 No Token (401 Unauthorized)
```bash
curl -s http://localhost:8080/api/medication
# Expected: {"detail":"Not authenticated"}
```

### 2.2 Invalid Role (403 Forbidden)
```bash
curl -s http://localhost:8080/api/medication \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Expected: {"detail":"Requires one of: ['patient', 'doctor']. Your roles: ['admin']"}
```

---

## Step 3: Test Per-Operation RBAC on Medication

### 3.1 Patient CAN Read (access: [patient, doctor])
```bash
curl -s http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq
```

### 3.2 Patient CAN Create (access: [patient, doctor])
```bash
curl -s -X POST http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aspirin",
    "dosage": "81mg",
    "frequency": "daily"
  }' | jq
# Expected: 201 Created
```

### 3.3 Patient CANNOT Update (access: [doctor] only)
```bash
curl -s -X PUT http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lisinopril",
    "dosage": "20mg",
    "frequency": "daily"
  }'
# Expected: {"detail":"Requires one of: ['doctor']. Your roles: ['patient']"}
```

### 3.4 Patient CANNOT Delete (access: [doctor] only)
```bash
curl -s -X DELETE http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN"
# Expected: {"detail":"Requires one of: ['doctor']. Your roles: ['patient']"}
```

### 3.5 Doctor CAN Update
```bash
curl -s -X PUT http://localhost:8080/api/medication \
  -H "Authorization: Bearer $DOCTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Metformin",
    "dosage": "500mg",
    "frequency": "twice daily"
  }' | jq
# Expected: 200 OK
```

### 3.6 Doctor CAN Delete
```bash
curl -s -X DELETE http://localhost:8080/api/medication \
  -H "Authorization: Bearer $DOCTOR_TOKEN"
# Expected: 204 No Content
```

---

## Step 4: Test Role-Exclusive Endpoints

### 4.1 HealthGoal - Patient Only
```bash
# Patient CAN access
curl -s http://localhost:8080/api/healthgoal \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq

# Doctor CANNOT access
curl -s http://localhost:8080/api/healthgoal \
  -H "Authorization: Bearer $DOCTOR_TOKEN"
# Expected: {"detail":"Requires one of: ['patient']. Your roles: ['doctor']"}
```

### 4.2 Patient Can Create Goals
```bash
curl -s -X POST http://localhost:8080/api/healthgoal \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "weight_loss",
    "target_value": 5.0,
    "deadline": "2025-06-01"
  }' | jq
```

---

## Step 5: Test Shared Endpoints

### 5.1 PatientProfile (access: [patient, doctor])
```bash
# Both can read
curl -s http://localhost:8080/api/patientprofile \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq

curl -s http://localhost:8080/api/patientprofile \
  -H "Authorization: Bearer $DOCTOR_TOKEN" | jq
```

### 5.2 Update Patient Profile
```bash
curl -s -X PUT http://localhost:8080/api/patientprofile \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "age": 35,
    "weight_kg": 80,
    "height_cm": 175,
    "emergency_contact": "+1-555-0123"
  }' | jq
```

### 5.3 VitalsSnapshot (read-only)
```bash
curl -s http://localhost:8080/api/vitalssnapshot \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq
```

---

## Step 6: Test Composite Entities

### 6.1 HealthSummary (computed BMI, status)
```bash
curl -s http://localhost:8080/api/healthsummary \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq
```

**Expected response:**
```json
{
  "patient_name": "John Doe",
  "bmi": 26.1,
  "bmi_category": "overweight",
  "heart_rate": 82,
  "blood_pressure": "129/81",
  "bp_status": "normal",
  "oxygen_level": 99,
  "oxygen_status": "normal",
  "overall_status": "stable"
}
```

---

## Step 7: Test WebSocket Endpoints

### 7.1 HeartRateMonitor (inbound - public)
```bash
wscat -c ws://localhost:8080/ws/heartratemonitor
```

**Expected messages:**
```json
{
  "current_bpm": 132,
  "timestamp": 1736500000,
  "status": "critical",
  "needs_attention": true
}
```

### 7.2 EmergencyAlert (outbound - requires patient role)
```bash
wscat -c "ws://localhost:8080/ws/emergencyalert?token=$PATIENT_TOKEN"
```

Then send:
```json
{"cause": "chest_pain", "severity": "high", "location": "Home", "message": "Experiencing chest pain"}
```

---

## Quick Test Script

```bash
#!/bin/bash
echo "=== Health Monitoring RBAC Tests ==="

# Generate tokens first
PATIENT_TOKEN=$(python -c "import jwt,time; print(jwt.encode({'sub':'p1','roles':['patient'],'exp':int(time.time())+3600}, 'hrVuSfeEwAr00Ebgs2ApeI0HfV1xxqXS', algorithm='HS256'))")
DOCTOR_TOKEN=$(python -c "import jwt,time; print(jwt.encode({'sub':'d1','roles':['doctor'],'exp':int(time.time())+3600}, 'hrVuSfeEwAr00Ebgs2ApeI0HfV1xxqXS', algorithm='HS256'))")
ADMIN_TOKEN=$(python -c "import jwt,time; print(jwt.encode({'sub':'a1','roles':['admin'],'exp':int(time.time())+3600}, 'hrVuSfeEwAr00Ebgs2ApeI0HfV1xxqXS', algorithm='HS256'))")

echo ""
echo "1. No auth (should be 401):"
curl -s -w " [HTTP %{http_code}]" http://localhost:8080/api/medication
echo ""

echo ""
echo "2. Invalid role (should be 403):"
curl -s -w " [HTTP %{http_code}]" http://localhost:8080/api/medication \
  -H "Authorization: Bearer $ADMIN_TOKEN"
echo ""

echo ""
echo "3. Patient READ medication (should be 200):"
curl -s -w " [HTTP %{http_code}]" http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN"
echo ""

echo ""
echo "4. Patient CREATE medication (should be 201):"
curl -s -w " [HTTP %{http_code}]" -X POST http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"TestMed","dosage":"10mg","frequency":"daily"}'
echo ""

echo ""
echo "5. Patient UPDATE medication (should be 403):"
curl -s -w " [HTTP %{http_code}]" -X PUT http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"TestMed","dosage":"20mg","frequency":"daily"}'
echo ""

echo ""
echo "6. Patient DELETE medication (should be 403):"
curl -s -w " [HTTP %{http_code}]" -X DELETE http://localhost:8080/api/medication \
  -H "Authorization: Bearer $PATIENT_TOKEN"
echo ""

echo ""
echo "7. Doctor UPDATE medication (should be 200):"
curl -s -w " [HTTP %{http_code}]" -X PUT http://localhost:8080/api/medication \
  -H "Authorization: Bearer $DOCTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"DocMed","dosage":"50mg","frequency":"weekly"}'
echo ""

echo ""
echo "8. Doctor DELETE medication (should be 204):"
curl -s -w " [HTTP %{http_code}]" -X DELETE http://localhost:8080/api/medication \
  -H "Authorization: Bearer $DOCTOR_TOKEN"
echo ""

echo ""
echo "9. Doctor access HealthGoal (should be 403 - patient only):"
curl -s -w " [HTTP %{http_code}]" http://localhost:8080/api/healthgoal \
  -H "Authorization: Bearer $DOCTOR_TOKEN"
echo ""

echo ""
echo "10. HealthSummary (computed entity):"
curl -s http://localhost:8080/api/healthsummary \
  -H "Authorization: Bearer $PATIENT_TOKEN" | jq

echo ""
echo "=== WebSocket Tests (run separately) ==="
echo "wscat -c ws://localhost:8080/ws/heartratemonitor"
echo "wscat -c \"ws://localhost:8080/ws/emergencyalert?token=\$PATIENT_TOKEN\""
```

---

## RBAC Summary Table

### Medication Entity
| Operation | Patient | Doctor |
|-----------|---------|--------|
| read | ✅ 200 | ✅ 200 |
| create | ✅ 201 | ✅ 201 |
| update | ❌ 403 | ✅ 200 |
| delete | ❌ 403 | ✅ 204 |

### Other Entities
| Entity | Patient | Doctor |
|--------|---------|--------|
| PatientProfile | ✅ read/update | ✅ read/update |
| VitalsSnapshot | ✅ read | ✅ read |
| HealthGoal | ✅ full CRUD | ❌ 403 |
| HealthSummary | ✅ read | ✅ read |
| HeartRateMonitor (WS) | ✅ public | ✅ public |
| EmergencyAlert (WS) | ✅ publish | ❌ 403 |
