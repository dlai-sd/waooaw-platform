# DependencyIsolationRequestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**manifest_version** | **str** |  | 
**dependency_ref** | **str** |  | 
**dependency_state** | **str** |  | 
**candidate_affected_skill_refs** | **List[str]** |  | 

## Example

```python
from employment_domain_client.models.dependency_isolation_request_v1 import DependencyIsolationRequestV1

# TODO update the JSON string below
json = "{}"
# create an instance of DependencyIsolationRequestV1 from a JSON string
dependency_isolation_request_v1_instance = DependencyIsolationRequestV1.from_json(json)
# print the JSON string representation of the object
print(DependencyIsolationRequestV1.to_json())

# convert the object into a dict
dependency_isolation_request_v1_dict = dependency_isolation_request_v1_instance.to_dict()
# create an instance of DependencyIsolationRequestV1 from a dict
dependency_isolation_request_v1_from_dict = DependencyIsolationRequestV1.from_dict(dependency_isolation_request_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


