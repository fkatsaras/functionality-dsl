"""
Postman Collection generator from OpenAPI specification.

Generates a Postman Collection v2.1 JSON file that can be imported into Postman
for API testing and documentation.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List


def generate_postman_collection(openapi_file: Path, output_dir: Path):
    """
    Generate Postman Collection v2.1 from OpenAPI spec.

    Args:
        openapi_file: Path to openapi.yaml file
        output_dir: Path to output directory
    """
    # Load OpenAPI spec
    with open(openapi_file, 'r', encoding='utf-8') as f:
        openapi_spec = yaml.safe_load(f)

    # Extract metadata
    info = openapi_spec.get('info', {})
    servers = openapi_spec.get('servers', [])
    base_url = servers[0]['url'] if servers else 'http://localhost:8080'

    # Create Postman collection structure
    collection = {
        "info": {
            "name": info.get('title', 'FDSL Generated API'),
            "description": info.get('description', ''),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": "fdsl-generated-collection",
        },
        "item": [],
        "variable": [
            {
                "key": "baseUrl",
                "value": base_url,
                "type": "string"
            }
        ]
    }

    # Group requests by tags (entity names)
    paths = openapi_spec.get('paths', {})
    schemas = openapi_spec.get('components', {}).get('schemas', {})

    # Organize by tags (entities)
    folders = {}

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'delete', 'patch']:
                continue

            tags = operation.get('tags', ['Default'])
            tag = tags[0] if tags else 'Default'

            if tag not in folders:
                folders[tag] = {
                    "name": tag,
                    "item": []
                }

            # Create request item
            request_item = _create_request_item(
                path, method, operation, schemas, base_url
            )
            folders[tag]['item'].append(request_item)

    # Add folders to collection
    collection['item'] = list(folders.values())

    # Write to file
    output_file = output_dir / "app" / "api" / "postman_collection.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2)

    print(f"[GENERATED] Postman collection: {output_file}")


def _create_request_item(path: str, method: str, operation: Dict, schemas: Dict, base_url: str) -> Dict:
    """Create a Postman request item from OpenAPI operation."""

    # Convert path parameters to Postman format
    # OpenAPI: /api/users/{userId} -> Postman: /api/users/:userId
    postman_path = path.replace('{', ':').replace('}', '')

    request_item = {
        "name": operation.get('summary', f"{method.upper()} {path}"),
        "request": {
            "method": method.upper(),
            "header": [
                {
                    "key": "Content-Type",
                    "value": "application/json",
                    "type": "text"
                }
            ],
            "url": {
                "raw": f"{{{{baseUrl}}}}{postman_path}",
                "host": ["{{baseUrl}}"],
                "path": [p for p in postman_path.split('/') if p],
                "variable": [],
                "query": []
            },
            "description": operation.get('description', '')
        },
        "response": []
    }

    # Add path parameters
    parameters = operation.get('parameters', [])
    for param in parameters:
        if param.get('in') == 'path':
            request_item['request']['url']['variable'].append({
                "key": param['name'],
                "value": f"<{param['name']}>",
                "description": param.get('description', '')
            })
        elif param.get('in') == 'query':
            request_item['request']['url']['query'].append({
                "key": param['name'],
                "value": "",
                "description": param.get('description', ''),
                "disabled": not param.get('required', False)
            })

    # Add request body if present
    request_body = operation.get('requestBody')
    if request_body:
        content = request_body.get('content', {})
        json_content = content.get('application/json', {})
        schema_ref = json_content.get('schema', {}).get('$ref')

        if schema_ref:
            schema_name = schema_ref.split('/')[-1]
            schema = schemas.get(schema_name, {})
            example_body = _generate_example_from_schema(schema)

            request_item['request']['body'] = {
                "mode": "raw",
                "raw": json.dumps(example_body, indent=2),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }

    # Add tests for response validation
    tests = _generate_tests(operation, method)
    if tests:
        request_item['event'] = [{
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": tests
            }
        }]

    return request_item


def _generate_example_from_schema(schema: Dict) -> Dict:
    """Generate example JSON from OpenAPI schema."""
    example = {}
    properties = schema.get('properties', {})
    required = schema.get('required', [])

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get('type', 'string')

        if prop_type == 'string':
            example[prop_name] = f"<{prop_name}>"
        elif prop_type == 'integer':
            example[prop_name] = 0
        elif prop_type == 'number':
            example[prop_name] = 0.0
        elif prop_type == 'boolean':
            example[prop_name] = False
        elif prop_type == 'array':
            example[prop_name] = []
        elif prop_type == 'object':
            example[prop_name] = {}

    return example


def _generate_tests(operation: Dict, method: str) -> List[str]:
    """Generate Postman test scripts for response validation."""
    tests = []
    responses = operation.get('responses', {})

    # Check for successful status code
    for status_code, response in responses.items():
        if status_code.startswith('2'):  # 2xx success codes
            tests.append(f"pm.test('Status code is {status_code}', function () {{")
            tests.append(f"    pm.response.to.have.status({status_code});")
            tests.append("});")
            tests.append("")

            # Check response body structure
            content = response.get('content', {})
            if 'application/json' in content:
                tests.append("pm.test('Response has JSON body', function () {")
                tests.append("    pm.response.to.be.json;")
                tests.append("});")
                tests.append("")

            break  # Only check first success response

    # Add response time check
    tests.append("pm.test('Response time is less than 2000ms', function () {")
    tests.append("    pm.expect(pm.response.responseTime).to.be.below(2000);")
    tests.append("});")

    return tests
