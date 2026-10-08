# InductionRequirementSetV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**DomainEmploymentSchemaVersion**](DomainEmploymentSchemaVersion.md) |  | 
**manifest_version** | **str** |  | 
**requirement_set_version** | **str** |  | 
**requirements** | [**List[DomainRequirementV1]**](DomainRequirementV1.md) |  | 
**produced_at** | **datetime** |  | 

## Example

```python
from employment_domain_client.models.induction_requirement_set_v1 import InductionRequirementSetV1

# TODO update the JSON string below
json = "{}"
# create an instance of InductionRequirementSetV1 from a JSON string
induction_requirement_set_v1_instance = InductionRequirementSetV1.from_json(json)
# print the JSON string representation of the object
print(InductionRequirementSetV1.to_json())

# convert the object into a dict
induction_requirement_set_v1_dict = induction_requirement_set_v1_instance.to_dict()
# create an instance of InductionRequirementSetV1 from a dict
induction_requirement_set_v1_from_dict = InductionRequirementSetV1.from_dict(induction_requirement_set_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


