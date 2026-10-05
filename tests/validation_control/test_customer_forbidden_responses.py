from validation_control.customer_forbidden_responses import insert_missing_responses, is_customer_path, missing_operations


def test_customer_path_scope_excludes_service_only_relationship_routes() -> None:
    assert is_customer_path("/api/v1/customer-portal/interactions/portal/messages")
    assert is_customer_path("/api/v1/employment/relationships/{relationshipId}/workspace")
    assert not is_customer_path("/api/v1/employment/relationships/{relationshipId}/transitions")
    assert not is_customer_path("/api/v1/employment/relationships/{relationshipId}/offerability")


def test_missing_forbidden_responses_are_inserted_without_reformatting() -> None:
    source = """openapi: 3.1.0
paths:
  /api/v1/professionals/marketplace:
    get:
      responses:
        \"200\": { description: OK }
    post:
      responses: { \"200\": { description: OK } }
components: {}
"""
    specification = {
        "paths": {
            "/api/v1/professionals/marketplace": {
                "get": {"responses": {"200": {"description": "OK"}}},
                "post": {"responses": {"200": {"description": "OK"}}},
            }
        }
    }
    missing = missing_operations(specification)

    updated = insert_missing_responses(source, missing)

    assert updated.count("#/components/responses/IdentityForbidden") == 2
    assert '        "200": { description: OK }' in updated
