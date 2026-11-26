# EmploymentExperienceModeGateV1

Blocks only the named action with a side effect until the named mode reports ready; never blocks opening a screen.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action** | **str** |  | 
**requires_mode** | **str** |  | 
**message_key** | **str** |  | 

## Example

```python
from employment_domain_client.models.employment_experience_mode_gate_v1 import EmploymentExperienceModeGateV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceModeGateV1 from a JSON string
employment_experience_mode_gate_v1_instance = EmploymentExperienceModeGateV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceModeGateV1.to_json())

# convert the object into a dict
employment_experience_mode_gate_v1_dict = employment_experience_mode_gate_v1_instance.to_dict()
# create an instance of EmploymentExperienceModeGateV1 from a dict
employment_experience_mode_gate_v1_from_dict = EmploymentExperienceModeGateV1.from_dict(employment_experience_mode_gate_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


