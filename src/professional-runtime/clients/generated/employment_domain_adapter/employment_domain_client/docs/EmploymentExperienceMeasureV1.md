# EmploymentExperienceMeasureV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**measure_id** | **str** |  | 
**unit** | **str** |  | 
**evidence_source** | **str** |  | 
**freshness_seconds** | **int** |  | 

## Example

```python
from employment_domain_client.models.employment_experience_measure_v1 import EmploymentExperienceMeasureV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentExperienceMeasureV1 from a JSON string
employment_experience_measure_v1_instance = EmploymentExperienceMeasureV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentExperienceMeasureV1.to_json())

# convert the object into a dict
employment_experience_measure_v1_dict = employment_experience_measure_v1_instance.to_dict()
# create an instance of EmploymentExperienceMeasureV1 from a dict
employment_experience_measure_v1_from_dict = EmploymentExperienceMeasureV1.from_dict(employment_experience_measure_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


