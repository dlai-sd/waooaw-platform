# EmploymentExperienceToolV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**tool_id** | **str** |  | 
**label_key** | **str** |  | 
**label** | **str** |  | 
**icon** | **str** |  | 
**command** | **str** |  | 
**plan_level** | **str** |  | [optional] 
**component_id** | **str** |  | [optional] 
**flyout** | [**List[EmploymentExperienceFlyoutOptionV1]**](EmploymentExperienceFlyoutOptionV1.md) |  | [optional] 

## Example

```python
from employment_domain_client.models.employment_experience_tool_v1 import EmploymentExperienceToolV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceToolV1 from a JSON string
employment_experience_tool_v1_instance = EmploymentExperienceToolV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceToolV1.to_json())

# convert the object into a dict
employment_experience_tool_v1_dict = employment_experience_tool_v1_instance.to_dict()
# create an instance of EmploymentExperienceToolV1 from a dict
employment_experience_tool_v1_from_dict = EmploymentExperienceToolV1.from_dict(employment_experience_tool_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


