# EmploymentExperienceModeV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**mode_id** | **str** |  | 
**label_key** | **str** |  | 
**label** | **str** |  | 
**readiness_source** | **str** |  | 
**entries** | [**List[EmploymentExperienceNavigationEntryV1]**](EmploymentExperienceNavigationEntryV1.md) |  | 
**tool_groups** | [**List[EmploymentExperienceToolGroupV1]**](EmploymentExperienceToolGroupV1.md) |  | [optional] 
**gates** | [**List[EmploymentExperienceModeGateV1]**](EmploymentExperienceModeGateV1.md) |  | [optional] 

## Example

```python
from employment_domain_client.models.employment_experience_mode_v1 import EmploymentExperienceModeV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceModeV1 from a JSON string
employment_experience_mode_v1_instance = EmploymentExperienceModeV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceModeV1.to_json())

# convert the object into a dict
employment_experience_mode_v1_dict = employment_experience_mode_v1_instance.to_dict()
# create an instance of EmploymentExperienceModeV1 from a dict
employment_experience_mode_v1_from_dict = EmploymentExperienceModeV1.from_dict(employment_experience_mode_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


