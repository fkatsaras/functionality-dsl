from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# Hardcoded test data
STUDENTS = {
    "std-001": {"id": "std-001", "name": "Alice Johnson", "email": "alice@university.edu", "enrollmentYear": 2022},
    "std-002": {"id": "std-002", "name": "Bob Smith", "email": "bob@university.edu", "enrollmentYear": 2023},
}

COURSES = {
    "crs-001": {"id": "crs-001", "title": "Introduction to Computer Science", "credits": 4},
    "crs-002": {"id": "crs-002", "title": "Data Structures", "credits": 3},
}

ENROLLMENTS = {
    "enr-001": {"id": "enr-001", "studentId": "std-001", "courseId": "crs-001", "semester": "Fall 2023", "grade": "A"},
    "enr-002": {"id": "enr-002", "studentId": "std-001", "courseId": "crs-002", "semester": "Spring 2024", "grade": "B"},
    "enr-003": {"id": "enr-003", "studentId": "std-002", "courseId": "crs-001", "semester": "Fall 2023", "grade": "C"},
}

# Student endpoints
@app.route('/students/<id>', methods=['GET'])
def get_student(id):
    if id in STUDENTS:
        return jsonify(STUDENTS[id])
    return jsonify({"error": "Student not found"}), 404

@app.route('/students', methods=['POST'])
def create_student():
    data = request.json
    new_id = f"std-{len(STUDENTS) + 1:03d}"
    student = {"id": new_id, **data}
    STUDENTS[new_id] = student
    return jsonify(student), 201

@app.route('/students/<id>', methods=['PUT'])
def update_student(id):
    if id in STUDENTS:
        data = request.json
        STUDENTS[id].update(data)
        return jsonify(STUDENTS[id])
    return jsonify({"error": "Student not found"}), 404

@app.route('/students/<id>', methods=['DELETE'])
def delete_student(id):
    if id in STUDENTS:
        del STUDENTS[id]
        return '', 204
    return jsonify({"error": "Student not found"}), 404

# Course endpoints
@app.route('/courses/<id>', methods=['GET'])
def get_course(id):
    if id in COURSES:
        return jsonify(COURSES[id])
    return jsonify({"error": "Course not found"}), 404

# Enrollment endpoints
@app.route('/enrollments/<id>', methods=['GET'])
def get_enrollment(id):
    if id in ENROLLMENTS:
        return jsonify(ENROLLMENTS[id])
    return jsonify({"error": "Enrollment not found"}), 404

@app.route('/enrollments', methods=['POST'])
def create_enrollment():
    data = request.json
    new_id = f"enr-{len(ENROLLMENTS) + 1:03d}"
    enrollment = {"id": new_id, **data}
    ENROLLMENTS[new_id] = enrollment
    return jsonify(enrollment), 201

# List enrollments (optionally filtered)
@app.route('/enrollments', methods=['GET'])
def list_enrollments():
    student_id = request.args.get('studentId')
    course_id = request.args.get('courseId')

    results = list(ENROLLMENTS.values())

    if student_id:
        results = [e for e in results if e["studentId"] == student_id]

    if course_id:
        results = [e for e in results if e["courseId"] == course_id]

    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=True)
