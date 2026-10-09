# AirEmploymentProblemV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | 
**title** | **str** |  | 
**status** | **int** |  | 
**code** | **str** |  | 
**correlation_id** | **str** |  | 

## Example

```python
from employment_air_client.models.air_employment_problem_v1 import AirEmploymentProblemV1

# TODO update the JSON string below
json = "{}"
# create an instance of AirEmploymentProblemV1 from a JSON string
air_employment_problem_v1_instance = AirEmploymentProblemV1.from_json(json)
# print the JSON string representation of the object
print(AirEmploymentProblemV1.to_json())

# convert the object into a dict
air_employment_problem_v1_dict = air_employment_problem_v1_instance.to_dict()
# create an instance of AirEmploymentProblemV1 from a dict
air_employment_problem_v1_from_dict = AirEmploymentProblemV1.from_dict(air_employment_problem_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


