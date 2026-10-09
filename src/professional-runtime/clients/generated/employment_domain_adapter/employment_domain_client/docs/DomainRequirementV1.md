# DomainRequirementV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**requirement_ref** | **str** |  | 
**label** | **str** |  | 
**description** | **str** |  | [optional] 
**mandatory** | **bool** |  | 
**dependency_type** | **str** |  | 
**affected_skill_refs** | **List[str]** |  | 
**confirmation_class** | **str** |  | [optional] 

## Example

```python
from employment_domain_client.models.domain_requirement_v1 import DomainRequirementV1

# TODO update the JSON string below
json = "{}"
# create an instance of DomainRequirementV1 from a JSON string
domain_requirement_v1_instance = DomainRequirementV1.from_json(json)
# print the JSON string representation of the object
print(DomainRequirementV1.to_json())

# convert the object into a dict
domain_requirement_v1_dict = domain_requirement_v1_instance.to_dict()
# create an instance of DomainRequirementV1 from a dict
domain_requirement_v1_from_dict = DomainRequirementV1.from_dict(domain_requirement_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


