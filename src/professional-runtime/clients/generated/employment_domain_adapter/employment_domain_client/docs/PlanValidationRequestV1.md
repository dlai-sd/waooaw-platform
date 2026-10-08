# PlanValidationRequestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**manifest_version** | **str** |  | 
**requirement_set_version** | **str** |  | 
**plan_version** | **str** |  | 
**goal_type** | **str** |  | 
**skill_refs** | **List[str]** |  | 
**milestone_types** | **List[str]** |  | 
**source_version** | **str** |  | 

## Example

```python
from employment_domain_client.models.plan_validation_request_v1 import PlanValidationRequestV1

# TODO update the JSON string below
json = "{}"
# create an instance of PlanValidationRequestV1 from a JSON string
plan_validation_request_v1_instance = PlanValidationRequestV1.from_json(json)
# print the JSON string representation of the object
print(PlanValidationRequestV1.to_json())

# convert the object into a dict
plan_validation_request_v1_dict = plan_validation_request_v1_instance.to_dict()
# create an instance of PlanValidationRequestV1 from a dict
plan_validation_request_v1_from_dict = PlanValidationRequestV1.from_dict(plan_validation_request_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


