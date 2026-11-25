# EmploymentExperienceNavigationEntryV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**entry_id** | **str** |  | 
**label_key** | **str** |  | 
**label** | **str** |  | 
**icon** | **str** |  | 
**order** | **int** |  | 
**surface** | [**EmploymentExperienceNavigationSurfaceV1**](EmploymentExperienceNavigationSurfaceV1.md) |  | 
**audiences** | [**List[EmploymentExperienceAudienceV1]**](EmploymentExperienceAudienceV1.md) |  | 
**availability_gate** | **str** |  | 

## Example

```python
from employment_domain_client.models.employment_experience_navigation_entry_v1 import EmploymentExperienceNavigationEntryV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceNavigationEntryV1 from a JSON string
employment_experience_navigation_entry_v1_instance = EmploymentExperienceNavigationEntryV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceNavigationEntryV1.to_json())

# convert the object into a dict
employment_experience_navigation_entry_v1_dict = employment_experience_navigation_entry_v1_instance.to_dict()
# create an instance of EmploymentExperienceNavigationEntryV1 from a dict
employment_experience_navigation_entry_v1_from_dict = EmploymentExperienceNavigationEntryV1.from_dict(employment_experience_navigation_entry_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


