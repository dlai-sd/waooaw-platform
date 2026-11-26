# EmploymentExperienceToolGroupV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**group_id** | **str** |  | 
**label_key** | **str** |  | 
**label** | **str** |  | 
**tools** | [**List[EmploymentExperienceToolV1]**](EmploymentExperienceToolV1.md) |  | 

## Example

```python
from employment_domain_client.models.employment_experience_tool_group_v1 import EmploymentExperienceToolGroupV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceToolGroupV1 from a JSON string
employment_experience_tool_group_v1_instance = EmploymentExperienceToolGroupV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceToolGroupV1.to_json())

# convert the object into a dict
employment_experience_tool_group_v1_dict = employment_experience_tool_group_v1_instance.to_dict()
# create an instance of EmploymentExperienceToolGroupV1 from a dict
employment_experience_tool_group_v1_from_dict = EmploymentExperienceToolGroupV1.from_dict(employment_experience_tool_group_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


