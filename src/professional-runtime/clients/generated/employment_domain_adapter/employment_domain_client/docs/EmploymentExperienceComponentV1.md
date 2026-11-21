# EmploymentExperienceComponentV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**component_id** | **str** |  | 
**label** | **str** |  | 
**unit** | **str** |  | 
**kind** | **str** |  | 
**skill_id** | **str** |  | [optional] 
**counted_on** | **str** |  | 
**selectable_dimension** | [**EmploymentExperienceComponentV1SelectableDimension**](EmploymentExperienceComponentV1SelectableDimension.md) |  | [optional] 
**availability** | **str** |  | 
**activation_authority** | **str** |  | [optional] 

## Example

```python
from employment_domain_client.models.employment_experience_component_v1 import EmploymentExperienceComponentV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceComponentV1 from a JSON string
employment_experience_component_v1_instance = EmploymentExperienceComponentV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceComponentV1.to_json())

# convert the object into a dict
employment_experience_component_v1_dict = employment_experience_component_v1_instance.to_dict()
# create an instance of EmploymentExperienceComponentV1 from a dict
employment_experience_component_v1_from_dict = EmploymentExperienceComponentV1.from_dict(employment_experience_component_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


