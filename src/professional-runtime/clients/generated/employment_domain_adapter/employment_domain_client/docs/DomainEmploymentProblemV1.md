# DomainEmploymentProblemV1


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
from employment_domain_client.models.domain_employment_problem_v1 import DomainEmploymentProblemV1

# TODO update the JSON string below
json = "{}"
# create an instance of DomainEmploymentProblemV1 from a JSON string
domain_employment_problem_v1_instance = DomainEmploymentProblemV1.from_json(json)
# print the JSON string representation of the object
print(DomainEmploymentProblemV1.to_json())

# convert the object into a dict
domain_employment_problem_v1_dict = domain_employment_problem_v1_instance.to_dict()
# create an instance of DomainEmploymentProblemV1 from a dict
domain_employment_problem_v1_from_dict = DomainEmploymentProblemV1.from_dict(domain_employment_problem_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


