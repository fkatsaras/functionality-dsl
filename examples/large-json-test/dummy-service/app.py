"""
Dummy service that generates large JSON responses for testing FDSL
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uvicorn

app = FastAPI(title="Large Data Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data for realistic generation
FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry", "Iris", "Jack",
               "Kate", "Liam", "Mia", "Noah", "Olivia", "Peter", "Quinn", "Rose", "Sam", "Tina"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
COUNTRIES = ["USA", "UK", "Canada", "Germany", "France", "Spain", "Italy", "Japan", "Australia", "Brazil",
             "India", "China", "Mexico", "Netherlands", "Sweden", "Norway", "Denmark", "Finland", "Poland", "Portugal"]
CITIES = ["New York", "London", "Toronto", "Berlin", "Paris", "Madrid", "Rome", "Tokyo", "Sydney", "Rio",
          "Mumbai", "Beijing", "Mexico City", "Amsterdam", "Stockholm", "Oslo", "Copenhagen", "Helsinki", "Warsaw", "Lisbon"]
OCCUPATIONS = ["Engineer", "Designer", "Manager", "Analyst", "Developer", "Consultant", "Architect", "Specialist",
               "Director", "Coordinator", "Administrator", "Researcher", "Scientist", "Teacher", "Writer"]
TAGS = ["premium", "verified", "beta-tester", "early-adopter", "power-user", "contributor", "moderator", "vip"]


def generate_user_record(index: int, include_metadata: bool = False) -> Dict[str, Any]:
    """Generate a single user record"""
    user_id = f"user-{index:06d}"
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    country_idx = random.randint(0, len(COUNTRIES) - 1)

    user = {
        "id": user_id,
        "username": f"{first_name.lower()}.{last_name.lower()}{index}",
        "email": f"{first_name.lower()}.{last_name.lower()}{index}@example.com",
        "firstName": first_name,
        "lastName": last_name,
        "age": random.randint(18, 70),
        "country": COUNTRIES[country_idx],
        "city": CITIES[country_idx],
        "occupation": random.choice(OCCUPATIONS),
        "salary": round(random.uniform(30000, 200000), 2),
        "joinDate": (datetime.now() - timedelta(days=random.randint(1, 1825))).isoformat(),
        "isActive": random.random() > 0.2,
        "tags": random.sample(TAGS, k=random.randint(1, 4))
    }

    if include_metadata:
        user["metadata"] = {
            "lastLogin": (datetime.now() - timedelta(hours=random.randint(1, 720))).isoformat(),
            "loginCount": random.randint(5, 5000),
            "preferences": {
                "theme": random.choice(["light", "dark", "auto"]),
                "language": random.choice(["en", "es", "fr", "de", "ja"]),
                "notifications": random.choice([True, False])
            },
            "subscription": {
                "tier": random.choice(["free", "basic", "premium", "enterprise"]),
                "expiresAt": (datetime.now() + timedelta(days=random.randint(30, 365))).isoformat()
            }
        }

    return user


@app.get("/api/users")
async def get_users(
    count: int = Query(default=1000),
    include_metadata: bool = Query(default=False)
):
    """Generate a large array of user records"""
    print(f"Generating {count} user records (metadata: {include_metadata})")
    users = [generate_user_record(i, include_metadata) for i in range(1, count + 1)]
    print(f"Generated {len(users)} users")
    return users


@app.get("/api/analytics")
async def get_analytics(days: int = Query(default=30)):
    """Generate analytics data with daily metrics"""
    print(f"Generating analytics for {days} days")

    daily_metrics = []
    start_date = datetime.now() - timedelta(days=days)

    for day_offset in range(days):
        date = start_date + timedelta(days=day_offset)
        daily_metrics.append({
            "date": date.strftime("%Y-%m-%d"),
            "pageViews": random.randint(10000, 100000),
            "uniqueVisitors": random.randint(5000, 50000),
            "bounceRate": round(random.uniform(0.2, 0.7), 4),
            "avgSessionDuration": round(random.uniform(60, 600), 2),
            "topPages": [
                f"/page{i}" for i in random.sample(range(1, 100), k=10)
            ],
            "deviceBreakdown": {
                "desktop": round(random.uniform(0.3, 0.6), 2),
                "mobile": round(random.uniform(0.3, 0.5), 2),
                "tablet": round(random.uniform(0.05, 0.2), 2)
            }
        })

    top_products = [
        {
            "productId": f"prod-{i}",
            "name": f"Product {i}",
            "sales": random.randint(100, 10000),
            "revenue": round(random.uniform(1000, 100000), 2)
        }
        for i in range(1, 51)  # Top 50 products
    ]

    analytics = {
        "period": f"{days} days",
        "totalUsers": random.randint(50000, 500000),
        "totalRevenue": round(random.uniform(100000, 10000000), 2),
        "dailyMetrics": daily_metrics,
        "topProducts": top_products,
        "conversionRates": {
            "homepage": round(random.uniform(0.01, 0.1), 4),
            "product": round(random.uniform(0.05, 0.3), 4),
            "checkout": round(random.uniform(0.5, 0.9), 4)
        }
    }

    print(f"Generated analytics with {len(daily_metrics)} daily records")
    return analytics


def generate_employee(emp_id: int, dept_name: str) -> Dict[str, Any]:
    """Generate a single employee record"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    return {
        "id": f"emp-{emp_id:05d}",
        "name": f"{first_name} {last_name}",
        "role": random.choice(OCCUPATIONS),
        "department": dept_name,
        "salary": round(random.uniform(40000, 250000), 2),
        "projects": [f"project-{random.randint(1000, 9999)}" for _ in range(random.randint(1, 5))]
    }


def generate_department(dept_id: int, depth: int = 0) -> Dict[str, Any]:
    """Generate a department with employees and optional sub-departments"""
    dept_name = f"Department-{dept_id}"
    employee_count = random.randint(5, 20)

    dept = {
        "id": f"dept-{dept_id:03d}",
        "name": dept_name,
        "budget": round(random.uniform(500000, 5000000), 2),
        "employees": [
            generate_employee(dept_id * 1000 + i, dept_name)
            for i in range(1, employee_count + 1)
        ]
    }

    # Add sub-departments (only 1 level deep to keep response reasonable)
    if depth < 1 and random.random() > 0.5:
        sub_dept_count = random.randint(2, 4)
        dept["subDepartments"] = [
            generate_department(dept_id * 10 + i, depth + 1)
            for i in range(1, sub_dept_count + 1)
        ]
    else:
        dept["subDepartments"] = None

    return dept


@app.get("/api/organization")
async def get_organization():
    """Generate organizational structure with nested departments"""
    print("Generating organization structure")

    departments = [generate_department(i) for i in range(1, 11)]  # 10 main departments

    # Calculate total employees
    def count_employees(dept: Dict[str, Any]) -> int:
        count = len(dept["employees"])
        if dept.get("subDepartments"):
            count += sum(count_employees(sub) for sub in dept["subDepartments"])
        return count

    total_employees = sum(count_employees(dept) for dept in departments)

    org = {
        "companyName": "TechCorp Global Inc.",
        "totalEmployees": total_employees,
        "departments": departments,
        "locations": [
            {"city": city, "country": country, "employeeCount": random.randint(50, 500)}
            for city, country in zip(CITIES[:10], COUNTRIES[:10])
        ]
    }

    print(f"Generated organization with {len(departments)} departments and {total_employees} employees")
    return org


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "large-data-generator"}


if __name__ == "__main__":
    print("Starting Large Data Generator on port 9000...")
    uvicorn.run(app, host="0.0.0.0", port=9000)
